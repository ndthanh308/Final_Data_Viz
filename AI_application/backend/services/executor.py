from __future__ import annotations

import ast
import base64
import io
import os
import re
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

Path("/tmp/matplotlib").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
	import numpy as np
except Exception:  # pragma: no cover
	np = None

try:
	import seaborn as sns
except Exception:  # pragma: no cover
	sns = None


def _encode_fig_to_base64_png(fig: plt.Figure) -> str:
	buf = io.BytesIO()
	fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
	buf.seek(0)
	return base64.b64encode(buf.read()).decode("utf-8")


def _unwrap_code(code: str) -> str:
	t = (code or "").strip()
	if not t.startswith("```"):
		return t
	match = re.search(r"```(?:python|py)?\s*(.*?)```", t, flags=re.DOTALL | re.IGNORECASE)
	if match:
		return match.group(1).strip()
	return t.strip("`").strip()


def infer_used_tables(code: str, default_table: str | None) -> List[str]:
	used: List[str] = []
	for m in re.finditer(r"tables\s*\[\s*[\"']([^\"']+)[\"']\s*\]", code or ""):
		used.append(m.group(1))
	for m in re.finditer(r"tables\s*\.\s*get\(\s*[\"']([^\"']+)[\"']", code or ""):
		used.append(m.group(1))
	if (code or "").find("df") != -1 and default_table:
		used.append(default_table)
	seen = set()
	out: List[str] = []
	for t in used:
		if t not in seen:
			seen.add(t)
			out.append(t)
	return out


def load_tables_from_schemas(schemas: Dict[str, Any]) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, str]:
	if not isinstance(schemas, dict):
		raise ValueError("Thông tin schema không hợp lệ")

	raw_dir = schemas.get("raw_dir")
	default_table = schemas.get("default_table")
	tables_spec = schemas.get("tables")
	if not raw_dir or not isinstance(tables_spec, dict) or not tables_spec:
		raise ValueError("Cần có raw_dir và danh sách bảng trong multiple_csv_schemas")

	raw_root = Path(str(raw_dir)).expanduser().resolve()
	if not raw_root.exists() or not raw_root.is_dir():
		raise ValueError(f"Thư mục dữ liệu không tồn tại: {raw_root}")

	loaded: Dict[str, pd.DataFrame] = {}
	for table_name in tables_spec.keys():
		name = str(table_name)
		csv_file = (raw_root / f"{name}.csv").resolve()
		if raw_root not in csv_file.parents:
			raise ValueError(f"Đường dẫn CSV không hợp lệ: {csv_file}")
		if not csv_file.exists():
			raise ValueError(f"Không tìm thấy CSV cho bảng '{name}': {csv_file}")
		loaded[name] = pd.read_csv(csv_file)

	if not default_table or str(default_table) not in loaded:
		default_table = next(iter(loaded.keys()))

	return loaded, loaded[str(default_table)], str(default_table)


def safe_exec_analysis(
	code: str,
	df: pd.DataFrame,
	tables: Dict[str, pd.DataFrame],
	default_table: str,
	schemas: Dict[str, Any],
) -> Dict[str, Any]:
	"""Thực thi code trong môi trường giới hạn và trả về kết quả."""
	code = _unwrap_code(code)

	def validate_code(user_code: str) -> None:
		tree = ast.parse(user_code)
		banned_names = {
			"open",
			"exec",
			"eval",
			"compile",
			"__import__",
			"input",
		}
		banned_import_roots = {
			"os",
			"sys",
			"subprocess",
			"socket",
			"pathlib",
			"shutil",
			"requests",
			"http",
			"urllib",
			"ftplib",
			"paramiko",
			"shlex",
			"importlib",
			"builtins",
		}
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				for alias in node.names:
					root = alias.name.split(".")[0]
					if root in banned_import_roots:
						raise ValueError(f"Không cho phép import '{root}'")
			if isinstance(node, ast.ImportFrom):
				root = (node.module or "").split(".")[0]
				if node.level != 0 or root in banned_import_roots:
					raise ValueError(f"Không cho phép import '{root}'")
			if isinstance(node, ast.Name) and node.id in banned_names:
				raise ValueError(f"Không được sử dụng '{node.id}'")

	validate_code(code)

	real_import = __import__
	banned_import_roots = {
		"os",
		"sys",
		"subprocess",
		"socket",
		"pathlib",
		"shutil",
		"requests",
		"http",
		"urllib",
		"ftplib",
		"paramiko",
		"shlex",
		"importlib",
		"builtins",
	}

	def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
		root = (name or "").split(".")[0]
		if root in banned_import_roots:
			raise ImportError(f"Không cho phép import '{root}'")
		return real_import(name, globals, locals, fromlist, level)

	allowed_builtins = {
		"print": print,
		"Exception": Exception,
		"ValueError": ValueError,
		"RuntimeError": RuntimeError,
		"hasattr": hasattr,
		"getattr": getattr,
		"globals": globals,
		"locals": locals,
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
		"zip": zip,
		"map": map,
		"filter": filter,
		"next": next,
		"isinstance": isinstance,
		"type": type,
		"bool": bool,
		"list": list,
		"dict": dict,
		"set": set,
		"tuple": tuple,
		"str": str,
		"int": int,
		"float": float,
		"repr": repr,
		"__import__": safe_import,
	}

	def require_columns(user_df: pd.DataFrame, cols: List[str], df_name: str = "df") -> None:
		missing = [c for c in cols if c not in user_df.columns]
		if missing:
			raise ValueError(
				f"Thiếu cột bắt buộc trong {df_name}: {missing}. Cột hiện có: {list(user_df.columns)}"
			)

	def pick_first_column(user_df: pd.DataFrame, candidates: List[str]) -> str:
		for c in candidates:
			if c in user_df.columns:
				return c
		raise ValueError(
			f"Không tìm thấy cột phù hợp trong danh sách: {candidates}. Cột hiện có: {list(user_df.columns)}"
		)

	exec_globals = {
		"__builtins__": allowed_builtins,
		"pd": pd,
		"plt": plt,
		"df": df,
		"tables": tables,
		"schemas": schemas,
		"require_columns": require_columns,
		"pick_first_column": pick_first_column,
	}
	exec_globals["__name__"] = "__analysis__"
	if np is not None:
		exec_globals["np"] = np
	if sns is not None:
		exec_globals["sns"] = sns

	exec_locals: Dict[str, Any] = {}

	stdout_buf = io.StringIO()
	# Mỗi lần thực thi cần trạng thái Matplotlib sạch để tránh converter/trục cũ
	# làm hỏng biểu đồ mới, đặc biệt khi chuyển từ category sang datetime.
	plt.close("all")

	with redirect_stdout(stdout_buf):
		exec(code, exec_globals, exec_locals)

	after_figs = list(plt.get_fignums())
	images_b64: List[str] = []
	for n in after_figs:
		fig = plt.figure(n)
		images_b64.append(_encode_fig_to_base64_png(fig))

	result_obj = exec_locals.get("result") or exec_globals.get("result")
	if not isinstance(result_obj, dict):
		result_obj = {
			"summary": "Không tạo được biến result hợp lệ.",
			"tables": [],
			"figures": [],
			"used_tables": [],
		}

	used_tables_inferred = infer_used_tables(code, default_table)
	used_tables_reported: List[str] = []
	if isinstance(result_obj.get("used_tables"), list):
		used_tables_reported = [str(x) for x in result_obj.get("used_tables") or []]
	if not used_tables_reported:
		used_tables_reported = used_tables_inferred
	result_obj["used_tables"] = used_tables_reported

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

	plt.close("all")

	return {
		"stdout": stdout_buf.getvalue(),
		"summary": str(result_obj.get("summary", "")),
		"tables": tables_out,
		"images_base64_png": images_b64,
		"meta": {
			"python": sys.version,
			"used_tables": used_tables_reported,
			"default_table": default_table,
			"available_tables": sorted(list(tables.keys())),
		},
	}


def build_error_message(error: Exception) -> str:
	return f"Thực thi thất bại: {error}"


def build_error_traceback() -> str:
	return traceback.format_exc()
