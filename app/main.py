from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    # Chạy bằng `uvicorn app.main:app`
    from .graph import build_graph
except Exception:  # pragma: no cover
    # Chạy khi đứng trong thư mục `app`: `uvicorn main:app`
    from graph import build_graph


load_dotenv()


app = FastAPI(title="HITL Multi-Agent Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


artifacts = build_graph()
graph = artifacts.graph


def _config(session_id: str) -> Dict[str, Any]:
    return {"configurable": {"thread_id": session_id}}


def _chuan_hoa_csv_context(csv_schemas_context: Any) -> Any:
    """Chuẩn hóa csv context từ frontend về dạng dict/list/text."""
    if isinstance(csv_schemas_context, (dict, list)):
        return csv_schemas_context
    if isinstance(csv_schemas_context, str):
        text = csv_schemas_context.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {"raw_text": text}
    return {}


def _snapshot_to_dict(snapshot: Any) -> Dict[str, Any]:
    return {
        "values": getattr(snapshot, "values", {}) or {},
        "next": list(getattr(snapshot, "next", ()) or ()),
        "metadata": getattr(snapshot, "metadata", None),
        "created_at": getattr(snapshot, "created_at", None),
        "config": getattr(snapshot, "config", None),
        "parent_config": getattr(snapshot, "parent_config", None),
    }


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Mã phiên làm việc")
    user_request: str = Field(..., min_length=1, description="Yêu cầu phân tích từ người dùng")
    csv_schemas_context: Union[Dict[str, Any], List[Dict[str, Any]], str, Any] = Field(
        default_factory=dict,
        description="Ngữ cảnh schema CSV dạng thô",
    )


class ChatResponse(BaseModel):
    session_id: str
    status: str
    generated_code: str
    execution_error: str = ""
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    approved_code: str = Field(..., min_length=1)


class ExecuteResponse(BaseModel):
    session_id: str
    status: str
    execution_result: Dict[str, Any] = Field(default_factory=dict)
    execution_error: str = ""
    insights: str = ""
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    state: Dict[str, Any]
    history: List[Dict[str, Any]]


@app.post("/api/ai/chat", response_model=ChatResponse)
def ai_chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id.strip()
    config = _config(session_id)
    csv_context = _chuan_hoa_csv_context(req.csv_schemas_context)

    try:
        # Khởi chạy graph đến điểm dừng phê duyệt (interrupt_before tool_executor).
        graph.invoke(
            {
                "session_id": session_id,
                "user_request": req.user_request.strip(),
                "csv_schemas": csv_context,
                "status": "received_request",
            },
            config=config,
        )
        snapshot = graph.get_state(config)
        values = (getattr(snapshot, "values", {}) or {}) if snapshot else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi sinh code: {e}")

    generated_code = str(values.get("generated_code", ""))
    if not generated_code:
        raise HTTPException(status_code=500, detail="Không nhận được generated_code từ Code Generator Agent.")

    return ChatResponse(
        session_id=session_id,
        status=str(values.get("status", "pending_approval")),
        generated_code=generated_code,
        execution_error=str(values.get("execution_error", "")),
        chat_history=values.get("chat_history", []) or [],
    )


@app.post("/api/ai/execute", response_model=ExecuteResponse)
def ai_execute(req: ExecuteRequest) -> ExecuteResponse:
    session_id = req.session_id.strip()
    config = _config(session_id)

    try:
        snapshot = graph.get_state(config)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên. Hãy gọi /api/ai/chat trước.")

        hien_tai = getattr(snapshot, "values", {}) or {}
        if str(hien_tai.get("status", "")) != "pending_approval":
            raise HTTPException(
                status_code=400,
                detail="Phiên hiện không ở trạng thái chờ duyệt code (`pending_approval`).",
            )

        graph.update_state(config, {"approved_code": req.approved_code.strip()})
        graph.invoke(None, config=config)
        sau_khi_chay = graph.get_state(config)
        values = (getattr(sau_khi_chay, "values", {}) or {}) if sau_khi_chay else {}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi code: {e}")

    return ExecuteResponse(
        session_id=session_id,
        status=str(values.get("status", "")),
        execution_result=values.get("execution_result", {}) or {},
        execution_error=str(values.get("execution_error", "")),
        insights=str(values.get("insights", "")),
        chat_history=values.get("chat_history", []) or [],
    )


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    sid = session_id.strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id không hợp lệ.")

    config = _config(sid)
    try:
        snapshot = graph.get_state(config)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên.")

        lich_su = []
        for item in graph.get_state_history(config):
            lich_su.append(_snapshot_to_dict(item))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin phiên: {e}")

    return SessionResponse(
        session_id=sid,
        state=_snapshot_to_dict(snapshot),
        history=lich_su,
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {
        "ok": "true",
        "model": os.getenv("OPENAI_MODEL", ""),
    }
