from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8001")


def _repo_root() -> Path:
	return Path(__file__).resolve().parents[1]


def _session_dir(session_id: str) -> Path:
	base = _repo_root() / ".hitl_sessions"
	base.mkdir(parents=True, exist_ok=True)
	path = base / session_id
	path.mkdir(parents=True, exist_ok=True)
	return path


def _sanitize_name(name: str) -> str:
	clean = "".join(ch for ch in name if ch.isalnum() or ch in {"_", "-"})
	return clean or "bang"


def _save_uploaded_files(files, session_id: str) -> List[Tuple[str, Path]]:
	out: List[Tuple[str, Path]] = []
	root = _session_dir(session_id)
	for f in files or []:
		name = _sanitize_name(Path(f.name).stem)
		path = root / f"{name}.csv"
		path.write_bytes(f.getvalue())
		out.append((name, path))
	return out


@st.cache_data(show_spinner=False)
def _load_schema_preview(csv_path: str, n_preview: int = 20, n_sample: int = 5) -> Dict[str, Any]:
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


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
	resp = requests.post(url, json=payload, timeout=180)
	resp.raise_for_status()
	return resp.json()


def _get_json(url: str) -> Dict[str, Any]:
	resp = requests.get(url, timeout=60)
	resp.raise_for_status()
	return resp.json()


def _render_execution_result(result: Dict[str, Any]) -> None:
	if not result:
		st.info("Chưa có kết quả thực thi")
		return

	if result.get("summary"):
		st.subheader("Tóm tắt")
		st.write(result["summary"])

	if result.get("stdout"):
		st.subheader("Nhật ký (stdout)")
		st.code(result["stdout"], language="text")

	images = result.get("images_base64_png") or []
	if images:
		st.subheader("Biểu đồ")
		for b64 in images:
			st.image(base64.b64decode(b64), use_container_width=True)

	tables = result.get("tables") or []
	if tables:
		st.subheader("Bảng kết quả")
		for t in tables:
			type_name = t.get("type")
			if type_name == "dataframe":
				st.dataframe(pd.DataFrame(t.get("data", [])), use_container_width=True)
			else:
				st.write(t)

	if result.get("meta"):
		with st.expander("Thông tin bổ sung", expanded=False):
			st.json(result["meta"])


def _init_state() -> None:
	if "session_id" not in st.session_state:
		st.session_state.session_id = ""
	if "session_list" not in st.session_state:
		st.session_state.session_list = []
	if "chat_history" not in st.session_state:
		st.session_state.chat_history = []
	if "generated_code" not in st.session_state:
		st.session_state.generated_code = ""
	if "last_generated_code" not in st.session_state:
		st.session_state.last_generated_code = ""
	if "approved_code" not in st.session_state:
		st.session_state.approved_code = ""
	if "pending_code_editor" not in st.session_state:
		st.session_state.pending_code_editor = None
	if "execution_result" not in st.session_state:
		st.session_state.execution_result = {}
	if "execution_error" not in st.session_state:
		st.session_state.execution_error = ""
	if "insights" not in st.session_state:
		st.session_state.insights = ""
	if "last_user_request" not in st.session_state:
		st.session_state.last_user_request = ""
	if "last_context" not in st.session_state:
		st.session_state.last_context = {}


def _new_session() -> str:
	return f"session-{uuid.uuid4().hex[:12]}"


def _queue_generated_code(state: Dict[str, Any], generated_code: str) -> None:
	state["generated_code"] = generated_code or ""
	state["approved_code"] = generated_code or ""
	state["last_generated_code"] = generated_code or ""
	state["pending_code_editor"] = generated_code or ""


def _apply_pending_code_editor(state: Dict[str, Any]) -> None:
	pending = state.get("pending_code_editor")
	if pending is None:
		return
	state["code_editor"] = pending
	state["pending_code_editor"] = None


# def _call_chat(prompt: str, ctx: Dict[str, Any]) -> None:
# 	payload = {
# 		"session_id": st.session_state.session_id,
# 		"user_request": prompt,
# 		"uploaded_files": ctx,
# 	}
# 	data = _post_json(f"{API_BASE}/api/ai/chat", payload)
# 	st.session_state.session_id = data.get("session_id", st.session_state.session_id)
# 	st.session_state.chat_history = data.get("chat_history", [])
# 	_queue_generated_code(st.session_state, data.get("generated_code", ""))
# 	st.session_state.insights = data.get("insights", "")
# 	st.session_state.execution_error = data.get("execution_error", "")
# 	if st.session_state.session_id not in st.session_state.session_list:
# 		st.session_state.session_list.append(st.session_state.session_id)

def _call_chat(prompt: str, ctx: Dict[str, Any]) -> None:
	payload = {
		"session_id": st.session_state.session_id,
		"user_request": prompt,
		"uploaded_files": ctx,
	}
	data = _post_json(f"{API_BASE}/api/ai/chat", payload)
	st.session_state.session_id = data.get("session_id", st.session_state.session_id)
	st.session_state.chat_history = data.get("chat_history", [])
	_queue_generated_code(st.session_state, data.get("generated_code", ""))
	st.session_state.insights = data.get("insights", "")
	st.session_state.execution_error = data.get("execution_error", "")
    
	# ====== THÊM DÒNG NÀY ĐỂ FIX LỖI HIỂN THỊ ======
	st.session_state.execution_result = {} 
	# ===============================================

	if st.session_state.session_id not in st.session_state.session_list:
		st.session_state.session_list.append(st.session_state.session_id)


def _call_execute() -> None:
    payload = {
        "session_id": st.session_state.session_id,
        "approved_code": st.session_state.approved_code,
    }
    data = _post_json(f"{API_BASE}/api/ai/execute", payload)
    
    # Lưu kết quả vào state hiện tại
    st.session_state.execution_result = data.get("execution_result", {})
    st.session_state.insights = data.get("insights", "")
    
    # Cập nhật chat_history từ backend (thường chứa các text phản hồi)
    st.session_state.chat_history = data.get("chat_history", [])
    
    # QUAN TRỌNG: Đính kèm execution_result vào tin nhắn cuối cùng để render lại sau này
    if st.session_state.chat_history and st.session_state.execution_result:
        st.session_state.chat_history[-1]["execution_result"] = st.session_state.execution_result

def _render_chat_history() -> None:
    for m in st.session_state.chat_history:
        role = m.get("role", "assistant")
        with st.chat_message(role):
            # 1. Hiển thị văn bản tin nhắn
            st.write(m.get("content", ""))
            
            # 2. Nếu tin nhắn này có chứa kết quả thực thi (biểu đồ/bảng) thì vẽ nó ra
            if "execution_result" in m:
                _render_execution_result(m["execution_result"])


def _render_code_message() -> None:
	if not st.session_state.generated_code and not st.session_state.approved_code:
		return

	with st.chat_message("assistant"):
		st.markdown("**Mã phân tích đã tạo**")
		st.caption("Bạn có thể chỉnh sửa mã trước khi phê duyệt thực thi.")

		if st.session_state.generated_code != st.session_state.last_generated_code:
			st.session_state.approved_code = st.session_state.generated_code
			st.session_state.pending_code_editor = st.session_state.generated_code
			st.session_state.last_generated_code = st.session_state.generated_code

		_apply_pending_code_editor(st.session_state)
		st.session_state.approved_code = st.text_area(
			"Mã Python",
			value=st.session_state.approved_code,
			height=360,
			key="code_editor",
			label_visibility="collapsed",
		)

		col_run, col_copy = st.columns([1, 3])
		with col_run:
			if st.button("Phê duyệt và thực thi", key="phe_duyet"):
				try:
					_call_execute()
					st.rerun()
				except Exception as e:
					st.error(f"Lỗi khi thực thi: {e}")
		with col_copy:
			st.caption("Mã chỉ chạy sau khi bạn bấm phê duyệt.")


def _render_error_message(ctx: Dict[str, Any]) -> None:
	if not st.session_state.execution_error:
		return

	with st.chat_message("assistant"):
		st.error(st.session_state.execution_error)
		st.markdown("**Bạn muốn xử lý lỗi như thế nào?**")
		new_prompt = st.text_area(
			"Điều chỉnh yêu cầu",
			value=st.session_state.last_user_request,
			key="fix_prompt",
		)
		col1, col2, col3 = st.columns(3)
		with col1:
			if st.button("Sinh lại mã", key="thu_lai"):
				try:
					_call_chat(st.session_state.last_user_request, ctx)
					st.session_state.execution_error = ""
					st.rerun()
				except Exception as e:
					st.error(f"Không thể tạo lại mã: {e}")
		with col2:
			if st.button("Cập nhật yêu cầu", key="cap_nhat"):
				st.session_state.last_user_request = new_prompt
				try:
					_call_chat(new_prompt, ctx)
					st.session_state.execution_error = ""
					st.rerun()
				except Exception as e:
					st.error(f"Không thể tạo lại mã: {e}")
		with col3:
			if st.button("Chạy lại mã đang sửa", key="chay_lai_ma"):
				try:
					_call_execute()
					st.rerun()
				except Exception as e:
					st.error(f"Lỗi khi thực thi: {e}")


def _render_result_message() -> None:
	if not st.session_state.execution_result and not st.session_state.insights:
		return

	with st.chat_message("assistant"):
		if st.session_state.execution_result:
			_render_execution_result(st.session_state.execution_result)
		if st.session_state.insights:
			st.subheader("Nhận định / Gợi ý")
			st.write(st.session_state.insights)


def main() -> None:
	st.set_page_config(page_title="Trợ lý dữ liệu HITL", layout="wide")
	st.title("Trợ lý phân tích dữ liệu (HITL)")
	st.caption("Giám sát → Tạo mã → Phê duyệt → Thực thi → Chuyên gia phân tích")

	_init_state()

	with st.sidebar:
		st.subheader("Quản lý phiên")
		if st.button("Tạo phiên mới"):
			new_id = _new_session()
			st.session_state.session_id = new_id
			if new_id not in st.session_state.session_list:
				st.session_state.session_list.append(new_id)
			st.session_state.chat_history = []
			st.session_state.generated_code = ""
			st.session_state.last_generated_code = ""
			st.session_state.approved_code = ""
			st.session_state.pending_code_editor = ""
			st.session_state.execution_result = {}
			st.session_state.execution_error = ""
			st.session_state.insights = ""

		if st.session_state.session_list:
			selected = st.selectbox("Chọn phiên", st.session_state.session_list, index=0)
			st.session_state.session_id = selected

		manual_id = st.text_input("Nhập mã phiên để tải", value="")
		if st.button("Tải phiên"):
			try:
				data = _get_json(f"{API_BASE}/api/sessions/{manual_id}")
				state = data.get("state", {})
				st.session_state.session_id = data.get("session_id", manual_id)
				st.session_state.chat_history = data.get("chat_history", [])
				st.session_state.generated_code = state.get("generated_code", "")
				st.session_state.last_generated_code = st.session_state.generated_code
				st.session_state.approved_code = state.get("approved_code", "")
				st.session_state.pending_code_editor = st.session_state.approved_code or st.session_state.generated_code
				st.session_state.execution_result = state.get("execution_result", {})
				st.session_state.execution_error = state.get("execution_error", "")
				st.session_state.insights = state.get("insights", "")
				if st.session_state.session_id not in st.session_state.session_list:
					st.session_state.session_list.append(st.session_state.session_id)
			except Exception as e:
				st.error(f"Không tải được phiên: {e}")

		st.subheader("Máy chủ")
		st.write(API_BASE)
		if st.button("Kiểm tra sức khỏe"):
			try:
				st.json(_get_json(f"{API_BASE}/health"))
			except Exception as e:
				st.error(str(e))

	st.subheader("1) Tải dữ liệu CSV")
	files = st.file_uploader("Chọn nhiều file CSV", type=["csv"], accept_multiple_files=True)
	if st.session_state.session_id == "":
		st.session_state.session_id = _new_session()
		if st.session_state.session_id not in st.session_state.session_list:
			st.session_state.session_list.append(st.session_state.session_id)

	saved = _save_uploaded_files(files, st.session_state.session_id) if files else []
	if saved:
		st.success(f"Đã tải {len(saved)} file")

	selected_tables = [name for name, _ in saved]
	default_table = None
	if selected_tables:
		default_table = st.selectbox("Bảng mặc định (df)", options=selected_tables, index=0)
		ctx = _build_context(_session_dir(st.session_state.session_id), selected_tables, default_table)
		st.session_state.last_context = ctx
		with st.expander("Sơ đồ đã gửi", expanded=False):
			st.json(ctx)

		with st.expander("Xem nhanh bảng dữ liệu", expanded=False):
			for name, path in saved:
				preview = _load_schema_preview(str(path))
				st.markdown(f"**{name}**")
				st.dataframe(pd.DataFrame(preview.get("preview", [])), use_container_width=True)
	else:
		ctx = st.session_state.last_context or {}

	st.divider()
	st.subheader("Trò chuyện với trợ lý dữ liệu")

	with st.container(border=True):
		if not st.session_state.chat_history and not st.session_state.generated_code:
			with st.chat_message("assistant"):
				st.write("Bạn hãy tải CSV rồi hỏi tôi cần phân tích gì. Tôi sẽ sinh mã, chờ bạn chỉnh sửa/phê duyệt, sau đó hiển thị kết quả ngay trong cuộc trò chuyện.")

		_render_chat_history()
		_render_code_message()
		_render_error_message(ctx)
		_render_result_message()

	chat_text = st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích dữ liệu...")
	if chat_text:
		st.session_state.last_user_request = chat_text
		try:
			_call_chat(chat_text, ctx)
			st.rerun()
		except Exception as e:
			st.error(f"Lỗi khi gửi yêu cầu: {e}")


if __name__ == "__main__":
	main()
