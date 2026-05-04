from __future__ import annotations

import base64
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


def _repo_root() -> Path:
	return Path(__file__).resolve().parents[1]


def _default_raw_dir() -> Path:
	return _repo_root() / "data" / "main" / "raw"


def _list_raw_tables(raw_dir: Path) -> List[Tuple[str, Path]]:
	if not raw_dir.exists() or not raw_dir.is_dir():
		return []
	out: List[Tuple[str, Path]] = []
	for p in sorted(raw_dir.glob("*.csv")):
		name = p.stem
		out.append((name, p))
	return out


@st.cache_data(show_spinner=False)
def _load_schema_preview(csv_path: str, n_preview: int = 20, n_sample: int = 5) -> Dict[str, Any]:
	# Keep this lightweight; backend does the full read during execution.
	df_preview = pd.read_csv(csv_path, nrows=max(n_preview, n_sample))
	return {
		"columns": list(df_preview.columns),
		"dtypes": {c: str(df_preview[c].dtype) for c in df_preview.columns},
		"sample": df_preview.head(n_sample).to_dict(orient="records"),
		"preview": df_preview.head(n_preview).to_dict(orient="records"),
		"preview_rows": int(min(len(df_preview), n_preview)),
	}


def _build_context(raw_dir: Path, selected_tables: List[str], default_table: str) -> Dict[str, Any]:
	ctx_tables: Dict[str, Any] = {}
	for t in selected_tables:
		csv_path = raw_dir / f"{t}.csv"
		ctx_tables[t] = _load_schema_preview(str(csv_path))
	return {
		"raw_dir": str(raw_dir),
		"default_table": default_table,
		"tables": ctx_tables,
	}


def _infer_used_tables(code: str, default_table: str | None) -> List[str]:
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


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
	resp = requests.post(url, json=payload, timeout=120)
	resp.raise_for_status()
	return resp.json()


def _render_execution_result(result: Dict[str, Any]) -> None:
	if not result:
		st.info("No execution result")
		return

	if result.get("error"):
		st.error(result["error"])
		return

	if result.get("summary"):
		st.subheader("Summary")
		st.write(result["summary"])

	if result.get("stdout"):
		st.subheader("Stdout")
		st.code(result["stdout"], language="text")

	images = result.get("images_base64_png") or []
	if images:
		st.subheader("Charts")
		for b64 in images:
			st.image(base64.b64decode(b64), use_container_width=True)

	tables = result.get("tables") or []
	if tables:
		st.subheader("Tables")
		for t in tables:
			ttype = t.get("type")
			if ttype == "dataframe":
				st.dataframe(pd.DataFrame(t.get("data", [])), use_container_width=True)
			else:
				st.write(t)

	if result.get("meta"):
		with st.expander("Meta", expanded=False):
			st.json(result["meta"])


def main() -> None:
	st.set_page_config(page_title="HITL Data Analysis Tester", layout="wide")
	st.title("Human-in-the-loop Data Analysis (LangGraph + FastAPI)")
	st.caption("Generate code → Human approves/edits → Execute locally on backend")

	with st.sidebar:
		st.subheader("Mode")
		mode = st.radio("", options=["HITL Analysis", "Chat"], horizontal=False)

		st.subheader("Backend")
		api_base = st.text_input("API_BASE", value=API_BASE)
		st.write("Health check")
		if st.button("Ping /health"):
			try:
				r = requests.get(f"{api_base}/health", timeout=15)
				st.json(r.json())
			except Exception as e:
				st.error(str(e))

		st.divider()
		st.subheader("Logs")
		if st.button("Load logs"):
			try:
				r = requests.get(f"{api_base}/api/logs?limit=50", timeout=30)
				st.session_state.logs_items = r.json().get("items", [])
			except Exception as e:
				st.error(str(e))

		if "logs_items" in st.session_state:
			with st.expander("Recent logs", expanded=False):
				st.json(st.session_state.logs_items)

	# State
	if "thread_id" not in st.session_state:
		st.session_state.thread_id = ""
	if "generated_code" not in st.session_state:
		st.session_state.generated_code = ""
	if "explanation" not in st.session_state:
		st.session_state.explanation = ""
	if "approved_code" not in st.session_state:
		st.session_state.approved_code = ""
	if "csv_path" not in st.session_state:
		st.session_state.csv_path = ""
	if "exec_result" not in st.session_state:
		st.session_state.exec_result = None
	if "chat_messages" not in st.session_state:
		st.session_state.chat_messages = []
	if "last_context" not in st.session_state:
		st.session_state.last_context = {}

	if mode == "Chat":
		st.subheader("Chat")
		st.caption("Ask anything. If you want it grounded in your data, enable context and select tables below.")

		raw_dir_default = _default_raw_dir()
		raw_dir = Path(
			st.text_input(
				"Raw data folder (data/main/raw)",
				value=str(raw_dir_default),
				help="Optional: used only to provide schema context to the chat.",
			)
		).expanduser()
		tables = _list_raw_tables(raw_dir)
		table_names = [t[0] for t in tables]
		include_ctx = st.checkbox("Include dataset context", value=True)
		selected_tables = st.multiselect(
			"Tables to include as context",
			options=table_names,
			default=table_names[:1] if table_names else [],
			disabled=(not include_ctx or not table_names),
		)
		default_table = None
		if include_ctx and selected_tables:
			default_table = st.selectbox("Default table (for context)", options=selected_tables, index=0)
			ctx = _build_context(raw_dir, selected_tables, default_table)
		else:
			ctx = {}
		st.session_state.last_context = ctx

		for m in st.session_state.chat_messages:
			with st.chat_message(m["role"]):
				st.write(m["content"])

		prompt = st.chat_input("Message")
		if prompt:
			st.session_state.chat_messages.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.write(prompt)
			try:
				payload = {"message": prompt, "context": st.session_state.last_context if include_ctx else {}}
				data = _post_json(f"{api_base}/api/ai/chat", payload)
				answer = data.get("answer", "")
			except Exception as e:
				answer = f"Error: {e}"
			st.session_state.chat_messages.append({"role": "assistant", "content": answer})
			with st.chat_message("assistant"):
				st.write(answer)

		return

	col1, col2 = st.columns([1, 1], gap="large")

	with col1:
		st.subheader("1) Choose Tables + Request")
		raw_dir_default = _default_raw_dir()
		raw_dir = Path(
			st.text_input(
				"Raw data folder (data/main/raw)",
				value=str(raw_dir_default),
				help="Streamlit will scan this folder for *.csv tables.",
			)
		).expanduser()
		tables = _list_raw_tables(raw_dir)
		if not tables:
			st.error(f"No CSV tables found in: {raw_dir}")
			st.stop()

		table_names = [t[0] for t in tables]
		selected_tables = st.multiselect(
			"Tables to include (auto-loaded from raw)",
			options=table_names,
			default=[table_names[0]],
			help="Pick one or more tables; these will be available to the AI as `tables['name']`.",
		)
		if not selected_tables:
			st.warning("Select at least one table")
			st.stop()

		default_table = st.selectbox(
			"Default table (available as `df`)",
			options=selected_tables,
			index=0,
		)

		st.markdown("**Selected tables (UI):** " + ", ".join(selected_tables))

		user_request = st.text_area(
			"User request",
			value="Plot a simple trend over time and show top categories.",
			height=120,
		)

		ctx = _build_context(raw_dir, selected_tables, default_table)
		with st.expander("Context sent to AI (schema only)", expanded=False):
			st.json(ctx)

		with st.expander("Table previews", expanded=False):
			for t in selected_tables:
				csv_path = raw_dir / f"{t}.csv"
				schema = _load_schema_preview(str(csv_path))
				st.markdown(f"**{t}**")
				st.dataframe(pd.DataFrame(schema.get("preview", [])), use_container_width=True)

		if st.button("Generate code", type="primary"):
			if not user_request.strip():
				st.error("Please enter a request")
			else:
				payload = {
					"user_request": user_request,
					"context": ctx,
					"thread_id": st.session_state.thread_id or None,
				}
				try:
					data = _post_json(f"{api_base}/api/ai/generate", payload)
					st.session_state.thread_id = data.get("thread_id", "")
					st.session_state.generated_code = data.get("generated_code", "")
					st.session_state.explanation = data.get("explanation", "")
					st.session_state.approved_code = st.session_state.generated_code
					st.session_state.selected_tables = selected_tables
					st.session_state.default_table = default_table
					st.success(f"Generated. thread_id={st.session_state.thread_id}")
				except Exception as e:
					st.error(str(e))

	with col2:
		st.subheader("2) Review/Approve + Execute")
		st.text_input("thread_id", key="thread_id")

		selected_tables = st.session_state.get("selected_tables") or []
		default_table = st.session_state.get("default_table")
		if selected_tables:
			st.markdown("**Selected tables (from last generate):** " + ", ".join(selected_tables))

		if st.session_state.explanation:
			with st.expander("Explanation", expanded=True):
				st.write(st.session_state.explanation)

		st.session_state.approved_code = st.text_area(
			"Approved code (you can edit before executing)",
			value=st.session_state.approved_code,
			height=360,
		)

		if st.session_state.approved_code and selected_tables:
			used = _infer_used_tables(st.session_state.approved_code, default_table)
			st.markdown("**Tables used (inferred from code):** " + (", ".join(used) if used else "(none detected)"))

		if st.button("Approve & Execute"):
			if not st.session_state.thread_id:
				st.error("Missing thread_id. Generate code first.")
			elif not st.session_state.approved_code.strip():
				st.error("Approved code is empty")
			else:
				payload = {
					"thread_id": st.session_state.thread_id,
					"approved_code": st.session_state.approved_code,
				}
				try:
					data = _post_json(f"{api_base}/api/ai/execute", payload)
					st.session_state.exec_result = data.get("execution_result")
					st.success("Executed")
				except Exception as e:
					st.error(str(e))

		st.divider()
		st.subheader("3) Results")
		if st.session_state.exec_result:
			meta = (st.session_state.exec_result or {}).get("meta") or {}
			used_tables_reported = meta.get("used_tables") if isinstance(meta, dict) else None
			if used_tables_reported:
				st.markdown("**Tables used (reported by execution):** " + ", ".join([str(x) for x in used_tables_reported]))
			_render_execution_result(st.session_state.exec_result)
		else:
			st.info("No execution yet")


if __name__ == "__main__":
	main()


