from __future__ import annotations

import base64
import io
import json
import os
import sqlite3
import sys
import time
import ast
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")


class HITLState(TypedDict, total=False):
	user_request: str
	context: Dict[str, Any]
	generated_code: str
	explanation: str
	approved_code: str
	execution_result: Dict[str, Any]
	logs: List[str]
	thread_id: str


@dataclass
class GraphArtifacts:
	graph: Any
	checkpointer: Any
	db_path: Path


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj: Any) -> str:
	return json.dumps(obj, ensure_ascii=False, default=str)


def _safe_json_loads(text: str) -> Dict[str, Any]:
	t = (text or "").strip()
	if t.startswith("```"):
		t = t.strip("`")
		t = t.replace("json\n", "", 1).strip()
	try:
		return json.loads(t)
	except Exception:
		return {}


def get_llm() -> ChatOpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY is missing")
	return ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)


def chat_answer(user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
	"""General chat/Q&A with the LLM (no code execution).

	This is intentionally separate from the HITL graph so that:
	- it never triggers code generation/execution steps unless the user asks
	- UI can support "normal" chat not strictly tied to plotting
	"""
	msg = (user_message or "").strip()
	ctx = context if isinstance(context, dict) else {}
	if not msg:
		return "Please provide a message."

	llm = get_llm()
	sys_prompt = SystemMessage(
		content=(
			"You are a helpful data assistant. Answer the user's question directly and clearly. "
			"You MUST NOT execute any code. "
			"If the user asks for code, you may provide Python code snippets, but include explanations as comments inside the code. "
			"If dataset context is provided, use it to ground your answer (tables, columns, dtypes, samples). "
			"If context is missing, ask a short clarifying question."
		)
	)
	human = HumanMessage(
		content=(
			f"USER_MESSAGE:\n{msg}\n\n"
			f"OPTIONAL_DATASET_CONTEXT_JSON:\n{_json_dumps(ctx)}\n"
		)
	)
	resp = llm.invoke([sys_prompt, human])
	return (resp.content or "").strip()


def _add_log(state: HITLState, msg: str) -> HITLState:
	logs = list(state.get("logs", []))
	logs.append(f"[{_utc_now_iso()}] {msg}")
	return {**state, "logs": logs}


# -------------------------
# SQLite logging
# -------------------------


def init_db(db_path: Path) -> None:
	db_path.parent.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(db_path) as conn:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS hitl_logs (
			  id INTEGER PRIMARY KEY AUTOINCREMENT,
			  created_at TEXT NOT NULL,
			  thread_id TEXT NOT NULL,
			  user_request TEXT NOT NULL,
			  context_json TEXT,
			  generated_code TEXT,
			  explanation TEXT,
			  approved_code TEXT,
			  execution_result_json TEXT
			)
			"""
		)
		conn.commit()


def insert_log(db_path: Path, state: HITLState) -> None:
	init_db(db_path)
	with sqlite3.connect(db_path) as conn:
		conn.execute(
			"""
			INSERT INTO hitl_logs (
			  created_at, thread_id, user_request, context_json,
			  generated_code, explanation, approved_code, execution_result_json
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""" ,
			(
				_utc_now_iso(),
				str(state.get("thread_id", "")),
				str(state.get("user_request", "")),
				_json_dumps(state.get("context", {})),
				state.get("generated_code", ""),
				state.get("explanation", ""),
				state.get("approved_code", ""),
				_json_dumps(state.get("execution_result", {})),
			),
		)
		conn.commit()


def fetch_logs(db_path: Path, limit: int = 200) -> List[Dict[str, Any]]:
	init_db(db_path)
	with sqlite3.connect(db_path) as conn:
		conn.row_factory = sqlite3.Row
		rows = conn.execute(
			"SELECT * FROM hitl_logs ORDER BY id DESC LIMIT ?",
			(int(limit),),
		).fetchall()
	out: List[Dict[str, Any]] = []
	for r in rows:
		out.append({k: r[k] for k in r.keys()})
	return out


# -------------------------
# Graph nodes
# -------------------------


def generate_code_node(state: HITLState) -> HITLState:
	"""Generate analysis code only (no execution), with explanations as comments."""

	state = _add_log(state, "generate_code_node: started")
	user_request = state.get("user_request", "").strip()
	context = state.get("context", {})

	if not user_request:
		return _add_log(state, "generate_code_node: empty user_request")

	llm = get_llm()

	# IMPORTANT: We only pass schema/context, not the full dataset.
	# The generated code MUST be runnable locally later.
	sys_prompt = SystemMessage(
		content=(
			"You are an AI data analyst. You MUST ONLY generate Python code; you MUST NOT execute anything. "
			"Your output must be valid JSON with keys: generated_code, explanation. "
			"Rules for generated_code (must be runnable as-is):\n"
			"- Use pandas + matplotlib only.\n"
			"- You are given: tables (dict[str, pandas.DataFrame]), df (pandas.DataFrame default table), and context (dict schema).\n"
			"- Do NOT read files. Do NOT call network. Do NOT import anything.\n"
			"- Do NOT use placeholders like 'YOUR_COLUMN', 'TODO', or assume columns exist.\n"
			"- ALWAYS validate required tables/columns before using them.\n"
			"  If a requested column is missing, either choose a sensible alternative from available columns, OR raise ValueError with a clear message that lists available columns.\n"
			"- Prefer explicit table usage: tables['orders'] etc. Use df only for the default table.\n"
			"- Handle common messy data: parse datetimes, coerce numeric, handle NaNs, avoid crashing on empty data (return a summary message).\n"
			"- Plotting must be readable by default (avoid overlapping):\n"
			"  - Always create figures with explicit figsize (e.g., (10, 4) or larger).\n"
			"  - Always call plt.tight_layout() after plotting.\n"
			"  - If x labels are long or there are many categories, rotate x tick labels (e.g., 30-60 degrees) and/or use a horizontal bar chart.\n"
			"  - If there are many categories (>12), show top-N (e.g., top 10) and group the rest as 'Other' OR use horizontal bars.\n"
			"  - For time-series: sort by time, use a sensible frequency, and format dates to avoid clutter (e.g., monthly ticks).\n"
			"- Add natural-language explanations as Python comments inside the code (Vietnamese comments are ok).\n"
			"- Produce a variable named result (dict) with keys:\n"
			"  - 'summary' (str)\n"
			"  - 'tables' (list)  # list of small DataFrames/dicts\n"
			"  - 'figures' (list) # optional\n"
			"  - 'used_tables' (list[str]) # include every table name you actually read from\n"
			"Helpers available (no imports needed):\n"
			"- require_columns(df, cols, df_name='df') -> None (raises ValueError)\n"
			"- pick_first_column(df, candidates) -> str (raises ValueError)\n"
		)
	)

	user_prompt = HumanMessage(
		content=(
			"Generate analysis code for this request using ONLY the provided dataset schema/context.\n\n"
			f"USER_REQUEST:\n{user_request}\n\n"
			f"DATASET_CONTEXT_JSON:\n{_json_dumps(context)}\n"
		)
	)

	resp = llm.invoke([sys_prompt, user_prompt])
	parsed = _safe_json_loads(resp.content or "")
	generated_code = (parsed.get("generated_code") or "").strip()
	explanation = (parsed.get("explanation") or "").strip()

	# Fallback if model didn't follow JSON.
	if not generated_code:
		generated_code = (resp.content or "").strip()
		explanation = explanation or "Model did not return JSON. Using raw output."

	state = {
		**state,
		"generated_code": generated_code,
		"explanation": explanation,
	}
	state = _add_log(state, "generate_code_node: done")
	return state


def human_approval_node(state: HITLState) -> HITLState:
	"""Dummy node to represent human approval step (graph will interrupt before execution)."""
	return _add_log(state, "human_approval_node: awaiting approval")


def _encode_fig_to_base64_png(fig: plt.Figure) -> str:
	buf = io.BytesIO()
	fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
	buf.seek(0)
	return base64.b64encode(buf.read()).decode("utf-8")


def _infer_used_tables_from_code(code: str, default_table: Optional[str]) -> List[str]:
	# Best-effort inference for UI display/logging.
	# Recognizes: tables["orders"], tables['orders'], tables.get("orders"), tables.get('orders')
	used: List[str] = []
	for m in re.finditer(r"tables\s*\[\s*[\"']([^\"']+)[\"']\s*\]", code or ""):
		used.append(m.group(1))
	for m in re.finditer(r"tables\s*\.\s*get\(\s*[\"']([^\"']+)[\"']", code or ""):
		used.append(m.group(1))
	if (code or "").find("df") != -1 and default_table:
		used.append(default_table)
	# Dedupe in order.
	seen = set()
	out: List[str] = []
	for t in used:
		if t not in seen:
			seen.add(t)
			out.append(t)
	return out


def _safe_exec_analysis(
	code: str,
	df: pd.DataFrame,
	tables: Dict[str, pd.DataFrame],
	default_table: Optional[str],
	context: Dict[str, Any],
) -> Dict[str, Any]:
	"""Execute approved code locally in a restricted environment.

	This is NOT a perfect sandbox (Python is hard to fully sandbox), but we reduce risk by:
	- providing a minimal set of builtins
	- not exposing file/network utilities
	- pre-providing df/pd/plt
	"""

	def _validate_code(user_code: str) -> None:
		"""Best-effort validation to block obviously dangerous code.

		Note: This is not a perfect sandbox, but it enforces HITL constraints:
		- no import statements
		- no file/network/process primitives
		- no direct use of __import__/exec/eval/open
		"""

		tree = ast.parse(user_code)
		banned_names = {
			"open",
			"exec",
			"eval",
			"compile",
			"__import__",
			"input",
			"globals",
			"locals",
			"vars",
			"dir",
			"help",
			"breakpoint",
		}
		banned_modules = {
			"os",
			"sys",
			"subprocess",
			"socket",
			"pathlib",
			"shlex",
			"importlib",
			"builtins",
		}

		for node in ast.walk(tree):
			if isinstance(node, (ast.Import, ast.ImportFrom)):
				raise ValueError("Import statements are not allowed in approved_code.")
			if isinstance(node, ast.Name) and node.id in banned_names:
				raise ValueError(f"Use of '{node.id}' is not allowed.")
			if isinstance(node, ast.Name) and node.id in banned_modules:
				raise ValueError(f"Use of module name '{node.id}' is not allowed.")
			if isinstance(node, ast.Attribute) and isinstance(node.attr, str) and node.attr.startswith("__"):
				raise ValueError("Access to dunder attributes is not allowed.")

	_validate_code(code)

	# Allow-listed import: needed because pandas/matplotlib perform internal imports.
	real_import = __import__
	allowed_import_roots = {
		"pandas",
		"numpy",
		"matplotlib",
		"dateutil",
		"pytz",
		"math",
		"statistics",
		"re",
		"collections",
		"itertools",
		"functools",
		"operator",
		"decimal",
		"typing",
	}

	def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
		root = (name or "").split(".")[0]
		if root not in allowed_import_roots:
			raise ImportError(f"Import of '{root}' is blocked by policy")
		return real_import(name, globals, locals, fromlist, level)

	allowed_builtins = {
		"print": print,
		"Exception": Exception,
		"ValueError": ValueError,
		"RuntimeError": RuntimeError,
		"hasattr": hasattr,
		"getattr": getattr,
		"len": len,
		"range": range,
		"min": min,
		"max": max,
		"sum": sum,
		"sorted": sorted,
		"any": any,
		"all": all,
		"abs": abs,
		"round": round,
		"enumerate": enumerate,
		"isinstance": isinstance,
		"type": type,
		"list": list,
		"dict": dict,
		"set": set,
		"tuple": tuple,
		"str": str,
		"int": int,
		"float": float,
		"__import__": safe_import,
	}

	def require_columns(user_df: pd.DataFrame, cols: List[str], df_name: str = "df") -> None:
		missing = [c for c in cols if c not in user_df.columns]
		if missing:
			raise ValueError(
				f"Missing required columns in {df_name}: {missing}. Available columns: {list(user_df.columns)}"
			)

	def pick_first_column(user_df: pd.DataFrame, candidates: List[str]) -> str:
		for c in candidates:
			if c in user_df.columns:
				return c
		raise ValueError(
			f"None of the candidate columns exist: {candidates}. Available columns: {list(user_df.columns)}"
		)

	exec_globals = {
		"__builtins__": allowed_builtins,
		"pd": pd,
		"plt": plt,
		"df": df,
		"tables": tables,
		"context": context,
		"require_columns": require_columns,
		"pick_first_column": pick_first_column,
	}
	exec_locals: Dict[str, Any] = {}

	# Capture stdout.
	stdout_buf = io.StringIO()
	before_figs = set(plt.get_fignums())

	with redirect_stdout(stdout_buf):
		exec(code, exec_globals, exec_locals)

	# Collect figures.
	after_figs = [n for n in plt.get_fignums() if n not in before_figs]
	images_b64: List[str] = []
	for n in after_figs:
		fig = plt.figure(n)
		images_b64.append(_encode_fig_to_base64_png(fig))

	# Try to read result dict.
	result_obj = exec_locals.get("result") or exec_globals.get("result")
	if not isinstance(result_obj, dict):
		result_obj = {
			"summary": "No `result` dict was produced by the code.",
			"tables": [],
			"figures": [],
			"used_tables": [],
		}

	used_tables_inferred = _infer_used_tables_from_code(code, default_table)
	used_tables_reported: List[str] = []
	if isinstance(result_obj.get("used_tables"), list):
		used_tables_reported = [str(x) for x in result_obj.get("used_tables") or []]
	if not used_tables_reported:
		used_tables_reported = used_tables_inferred
	result_obj["used_tables"] = used_tables_reported

	# Convert DataFrames in tables to JSON-ish.
	tables_out: List[Dict[str, Any]] = []
	for t in result_obj.get("tables", []) if isinstance(result_obj.get("tables"), list) else []:
		if isinstance(t, pd.DataFrame):
			tables_out.append(
				{
					"type": "dataframe",
					"data": t.head(200).to_dict(orient="records"),
					"columns": list(t.columns),
				}
			)
		elif isinstance(t, dict):
			tables_out.append({"type": "dict", "data": t})
		else:
			tables_out.append({"type": "text", "data": str(t)})

	# Cleanup matplotlib state for next run.
	plt.close("all")

	return {
		"stdout": stdout_buf.getvalue(),
		"summary": str(result_obj.get("summary", "")),
		"tables": tables_out,
		"images_base64_png": images_b64,
		"meta": {
			"python": sys.version,
			"executed_at": _utc_now_iso(),
			"used_tables": used_tables_reported,
			"default_table": default_table,
			"available_tables": sorted(list(tables.keys())),
		},
	}


def _load_tables_from_context(context: Dict[str, Any]) -> tuple[Dict[str, pd.DataFrame], pd.DataFrame, Optional[str]]:
	"""Load tables for local execution.

	Supported context formats:
	- Single-table (legacy): {"csv_path": "/path/to/file.csv", ...}
	- Multi-table: {
	    "raw_dir": "/abs/path/to/data/main/raw",
	    "tables": {"orders": {...schema...}, "payments": {...}},
	    "default_table": "orders"
	  }
	Keys of `tables` are treated as table names; execution loads `${raw_dir}/{name}.csv`.
	"""
	if not isinstance(context, dict):
		context = {}

	csv_path = context.get("csv_path")
	if csv_path:
		df = pd.read_csv(str(csv_path))
		return {"df": df}, df, "df"

	raw_dir = context.get("raw_dir")
	tables_spec = context.get("tables")
	default_table = context.get("default_table")
	if not raw_dir or not isinstance(tables_spec, dict) or not tables_spec:
		raise ValueError("Execution context must include either context.csv_path or context.raw_dir + context.tables")

	raw_root = Path(str(raw_dir)).expanduser().resolve()
	if not raw_root.exists() or not raw_root.is_dir():
		raise ValueError(f"context.raw_dir does not exist or is not a directory: {raw_root}")

	loaded: Dict[str, pd.DataFrame] = {}
	for table_name in tables_spec.keys():
		name = str(table_name)
		csv_file = (raw_root / f"{name}.csv").resolve()
		# Ensure path is inside raw_root to prevent traversal.
		if raw_root not in csv_file.parents:
			raise ValueError(f"Blocked table path outside raw_dir: {csv_file}")
		if not csv_file.exists():
			raise ValueError(f"Missing CSV for table '{name}': {csv_file}")
		loaded[name] = pd.read_csv(csv_file)

	if not default_table or str(default_table) not in loaded:
		default_table = next(iter(loaded.keys()))

	return loaded, loaded[str(default_table)], str(default_table)


def execute_code_node(state: HITLState) -> HITLState:
	"""Execute ONLY the human-approved code locally and capture outputs."""

	state = _add_log(state, "execute_code_node: started")
	approved_code = (state.get("approved_code") or "").strip()
	context = state.get("context", {})

	if not approved_code:
		state = _add_log(state, "execute_code_node: missing approved_code")
		return {**state, "execution_result": {"error": "approved_code is required"}}

	try:
		tables, df, default_table = _load_tables_from_context(context)
	except Exception as e:
		return {**state, "execution_result": {"error": str(e)}}

	started = time.time()
	try:
		result = _safe_exec_analysis(approved_code, df, tables, default_table, context if isinstance(context, dict) else {})
		result["meta"]["elapsed_sec"] = round(time.time() - started, 4)
		state = {**state, "execution_result": result}
		state = _add_log(state, "execute_code_node: done")
		return state
	except Exception as e:
		state = {**state, "execution_result": {"error": str(e)}}
		state = _add_log(state, f"execute_code_node: error: {e}")
		return state


def log_node_factory(db_path: Path):
	def _log_node(state: HITLState) -> HITLState:
		state = _add_log(state, "log_node: started")
		try:
			insert_log(db_path, state)
			state = _add_log(state, "log_node: stored")
		except Exception as e:
			state = _add_log(state, f"log_node: failed: {e}")
		return state

	return _log_node


def build_graph(db_path: Optional[Path] = None) -> GraphArtifacts:
	base_dir = Path(__file__).parent
	db_path = db_path or (base_dir / "logs.db")

	builder = StateGraph(HITLState)
	builder.add_node("generate_code", generate_code_node)
	builder.add_node("human_approval", human_approval_node)
	builder.add_node("execute_code", execute_code_node)
	builder.add_node("log", log_node_factory(db_path))

	builder.add_edge(START, "generate_code")
	builder.add_edge("generate_code", "human_approval")
	builder.add_edge("human_approval", "execute_code")
	builder.add_edge("execute_code", "log")
	builder.add_edge("log", END)

	checkpointer = MemorySaver()
	# Interrupt BEFORE executing code to enforce Human-in-the-loop.
	graph = builder.compile(checkpointer=checkpointer, interrupt_before=["execute_code"])

	return GraphArtifacts(graph=graph, checkpointer=checkpointer, db_path=db_path)

