from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import fetch_logs, fetch_session, init_db, insert_log, save_session
from backend.graph import build_graph


load_dotenv()


app = FastAPI(title="API Phân tích Dữ liệu HITL", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

artifacts = build_graph()

graph = artifacts.graph
DB_PATH = artifacts.db_path
init_db(DB_PATH)


def _mk_config(session_id: str) -> Dict[str, Any]:
	return {"configurable": {"thread_id": session_id}}


def _new_session_id() -> str:
	return f"session-{uuid.uuid4().hex[:12]}"


def _load_persisted_state(session_id: str) -> Dict[str, Any]:
	row = fetch_session(DB_PATH, session_id)
	if not row:
		return {}
	try:
		return json.loads(row.get("state_json", "{}"))
	except Exception:
		return {}


def _restore_graph_state(session_id: str, state: Dict[str, Any], as_node: str = "human_approval") -> None:
	if not state:
		return
	graph.update_state(_mk_config(session_id), state, as_node=as_node)


class ChatRequest(BaseModel):
	session_id: Optional[str] = None
	user_request: str = Field(..., min_length=1)
	uploaded_files: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
	session_id: str
	message: str
	generated_code: str = ""
	execution_error: str = ""
	insights: str = ""
	supervisor_response: str = ""
	supervisor_observation: str = ""
	chat_history: list[Dict[str, str]] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
	session_id: str = Field(..., min_length=1)
	approved_code: str = Field(..., min_length=1)


class ExecuteResponse(BaseModel):
	session_id: str
	message: str
	execution_result: Dict[str, Any] = Field(default_factory=dict)
	execution_error: str = ""
	insights: str = ""
	supervisor_observation: str = ""
	chat_history: list[Dict[str, str]] = Field(default_factory=list)


@app.post("/api/ai/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
	session_id = req.session_id or _new_session_id()
	config = _mk_config(session_id)

	try:
		snap = graph.get_state(config)
		existing = getattr(snap, "values", {}) or {}
		history = list(existing.get("chat_history") or [])
	except Exception:
		existing = {}
		history = []

	history.append({"role": "user", "content": req.user_request})

	# payload: Dict[str, Any] = {
	# 	"session_id": session_id,
	# 	"user_request": req.user_request,
	# 	"multiple_csv_schemas": req.uploaded_files or existing.get("multiple_csv_schemas") or {},
	# 	"generated_code": existing.get("generated_code", ""),
	# 	"approved_code": "",
	# 	"execution_result": existing.get("execution_result", {}),
	# 	"execution_error": "",
	# 	"insights": existing.get("insights", ""),
	# 	"supervisor_response": "",
	# 	"supervisor_observation": "",
	# 	"next_node": "",
	# 	"chat_history": history,
	# }
	payload: Dict[str, Any] = {
		"session_id": session_id,
		"user_request": req.user_request,
		"multiple_csv_schemas": req.uploaded_files or existing.get("multiple_csv_schemas") or {},
		"generated_code": "",      # ✅ Bắt đầu lượt mới, xoá code cũ đi
		"approved_code": "",
		"execution_result": {},    # ✅ Xoá kết quả bảng/biểu đồ cũ
		"execution_error": "",
		"insights": "",            # ✅ Xoá trắng phần "Nhận định / Gợi ý" cũ
		"supervisor_response": "",
		"supervisor_observation": "",
		"next_node": "",
		"chat_history": history,
	}

	try:
		# Mỗi lượt chat là một input mới trong cùng thread_id. Không dùng invoke(None)
		# ở đây, vì None chỉ phù hợp khi resume sau human approval và khiến trace
		# LangSmith của lượt chat mới bị ghi input=null.
		state = graph.invoke(payload, config=config)
		save_session(DB_PATH, session_id, state)
		insert_log(DB_PATH, state)

		message = "Vui lòng kiểm tra và phê duyệt mã." if state.get("generated_code") else "Đã xử lý yêu cầu."
		return ChatResponse(
			session_id=session_id,
			message=message,
			generated_code=state.get("generated_code", "") or "",
			execution_error=state.get("execution_error", "") or "",
			insights=state.get("insights", "") or "",
			supervisor_response=state.get("supervisor_response", "") or "",
			supervisor_observation=state.get("supervisor_observation", "") or "",
			chat_history=state.get("chat_history", []) or [],
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý yêu cầu: {e}")


@app.post("/api/ai/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest) -> ExecuteResponse:
	config = _mk_config(req.session_id)

	try:
		snap = graph.get_state(config)
		if not getattr(snap, "next", None):
			persisted = _load_persisted_state(req.session_id)
			if persisted and persisted.get("generated_code"):
				_restore_graph_state(req.session_id, persisted, as_node="human_approval")
				snap = graph.get_state(config)
		if not getattr(snap, "next", None):
			raise HTTPException(
				status_code=400,
				detail="Không tìm thấy phiên hoặc không cho phép thực thi. Hãy gửi /api/ai/chat trước.",
			)
		if tuple(snap.next) != ("tool_executor",):
			raise HTTPException(
				status_code=400,
				detail=f"Phiên không ở trạng thái chờ phê duyệt (next={snap.next}).",
			)

		graph.update_state(config, {"approved_code": req.approved_code, "execution_error": ""})
		state = graph.invoke(None, config=config)
		save_session(DB_PATH, req.session_id, state)
		insert_log(DB_PATH, state)

		message = "Thực thi thành công." if not state.get("execution_error") else "Thực thi gặp lỗi."
		return ExecuteResponse(
			session_id=req.session_id,
			message=message,
			execution_result=state.get("execution_result", {}) or {},
			execution_error=state.get("execution_error", "") or "",
			insights=state.get("insights", "") or "",
			supervisor_observation=state.get("supervisor_observation", "") or "",
			chat_history=state.get("chat_history", []) or [],
		)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi: {e}")


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
	row = fetch_session(DB_PATH, session_id)
	if not row:
		raise HTTPException(status_code=404, detail="Không tìm thấy phiên")
	return {
		"session_id": row.get("session_id"),
		"updated_at": row.get("updated_at"),
		"state": json.loads(row.get("state_json", "{}")),
		"chat_history": json.loads(row.get("chat_history_json", "[]")),
	}


@app.get("/api/logs")
async def get_logs(limit: int = 50, session_id: Optional[str] = None):
	limit = max(1, min(int(limit), 200))
	return {"items": fetch_logs(DB_PATH, session_id=session_id, limit=limit)}


@app.get("/health")
async def health():
	return {
		"ok": True,
		"model": os.getenv("OPENAI_MODEL", ""),
		"code_model": os.getenv("OPENAI_CODE_MODEL", os.getenv("OPENAI_MODEL", "")),
	}
