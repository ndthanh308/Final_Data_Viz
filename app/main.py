from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
	# Preferred when running from repo root/Week02: `uvicorn app.main:app`
	from .graph import build_graph, fetch_logs, chat_answer
except Exception:  # pragma: no cover
	# Fallback when running from inside this folder: `uvicorn main:app`
	from graph import build_graph, fetch_logs, chat_answer


load_dotenv()


app = FastAPI(title="HITL Data Analysis API", version="0.1.0")

# Streamlit will typically run on another port; allow localhost usage.
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"] ,
	allow_headers=["*"],
)


artifacts = build_graph()
graph = artifacts.graph
DB_PATH = artifacts.db_path


def _mk_config(thread_id: str) -> Dict[str, Any]:
	return {"configurable": {"thread_id": thread_id}}


class GenerateRequest(BaseModel):
	user_request: str = Field(..., min_length=1)
	context: Dict[str, Any] = Field(default_factory=dict)
	thread_id: Optional[str] = None


class GenerateResponse(BaseModel):
	thread_id: str
	status: str
	generated_code: str
	explanation: str


class ExecuteRequest(BaseModel):
	thread_id: str = Field(..., min_length=1)
	approved_code: str = Field(..., min_length=1)


class ExecuteResponse(BaseModel):
	thread_id: str
	status: str
	execution_result: Dict[str, Any]
	logs: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
	message: str = Field(..., min_length=1)
	context: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
	answer: str


@app.post("/api/ai/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
	thread_id = req.thread_id or f"thread-{uuid.uuid4().hex[:10]}"
	config = _mk_config(thread_id)

	try:
		# Runs until it hits the interrupt before `execute_code`.
		state = graph.invoke(
			{
				"thread_id": thread_id,
				"user_request": req.user_request,
				"context": req.context,
				"logs": [],
			},
			config=config,
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	return GenerateResponse(
		thread_id=thread_id,
		status="pending_approval",
		generated_code=state.get("generated_code", ""),
		explanation=state.get("explanation", ""),
	)


@app.post("/api/ai/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest) -> ExecuteResponse:
	config = _mk_config(req.thread_id)

	try:
		snap = graph.get_state(config)
		if not getattr(snap, "next", None):
			raise HTTPException(
				status_code=400,
				detail="Unknown thread_id or no pending approval state. Call POST /api/ai/generate first.",
			)
		if tuple(snap.next) != ("execute_code",):
			raise HTTPException(
				status_code=400,
				detail=f"Thread is not waiting for approval (next={snap.next}). Call POST /api/ai/generate first.",
			)
		ctx = (getattr(snap, "values", {}) or {}).get("context", {})
		if not isinstance(ctx, dict):
			raise HTTPException(status_code=400, detail="Stored context is invalid. Provide context in POST /api/ai/generate.")
		if not (ctx.get("csv_path") or (ctx.get("raw_dir") and ctx.get("tables"))):
			raise HTTPException(
				status_code=400,
				detail="Missing execution context in stored state. Provide either context.csv_path OR context.raw_dir + context.tables in POST /api/ai/generate.",
			)

		# HITL requirement: update the stored state with user-approved code, then resume execution.
		graph.update_state(config, {"approved_code": req.approved_code})
		state = graph.invoke(None, config=config)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

	return ExecuteResponse(
		thread_id=req.thread_id,
		status="executed",
		execution_result=state.get("execution_result", {}) or {},
		logs=state.get("logs", []) or [],
	)


@app.get("/api/logs")
def get_logs(limit: int = 100):
	limit = max(1, min(int(limit), 500))
	return {"items": fetch_logs(DB_PATH, limit=limit)}


@app.post("/api/ai/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
	try:
		answer = chat_answer(req.message, req.context)
		return ChatResponse(answer=answer)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
	return {"ok": True, "model": os.getenv("OPENAI_MODEL", "")}

