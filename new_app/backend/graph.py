from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.agents import (
	answer_directly,
	create_insights,
	decide_next_node,
	generate_code,
	review_subagent_outputs,
)
from backend.services.executor import (
	build_error_message,
	build_error_traceback,
	load_tables_from_schemas,
	safe_exec_analysis,
)


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_CODE_MODEL = os.getenv("OPENAI_CODE_MODEL", OPENAI_MODEL)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

class AgentState(TypedDict, total=False):
	session_id: str
	chat_history: List[Dict[str, str]]
	multiple_csv_schemas: Dict[str, Any]
	user_request: str
	generated_code: str
	approved_code: str
	execution_result: Dict[str, Any]
	execution_error: str
	insights: str
	next_node: str
	supervisor_response: str
	supervisor_observation: str


@dataclass
class GraphArtifacts:
	graph: Any
	checkpointer: Any
	db_path: Path


def get_llm() -> ChatOpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("Thiếu OPENAI_API_KEY trong biến môi trường")
	# return ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)
	# return ChatOpenAI(model="inclusionai/ring-2.6-1t:free", base_url="https://openrouter.ai/api/v1", api_key=OPENAI_API_KEY, temperature=0.2)
	return ChatGoogleGenerativeAI(
		model="gemini-2.5-flash",
		temperature=0,
		api_key=GOOGLE_API_KEY,
		max_retries=0,
	)


def get_code_llm() -> ChatOpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("Thiếu OPENAI_API_KEY trong biến môi trường")
	# return ChatOpenAI(model=OPENAI_CODE_MODEL, api_key=OPENAI_API_KEY, temperature=0)
	# return ChatOpenAI(model="inclusionai/ring-2.6-1t:free", base_url="https://openrouter.ai/api/v1", api_key=OPENAI_API_KEY, temperature=0.2)
	return ChatGoogleGenerativeAI(
		model="gemini-2.5-flash",
		temperature=0,
		api_key=GOOGLE_API_KEY,
		max_retries=0,
	)


def _append_history(state: AgentState, role: str, content: str) -> AgentState:
	history = list(state.get("chat_history") or [])
	history.append({"role": role, "content": content})
	return {**state, "chat_history": history}


def supervisor_node(state: AgentState) -> AgentState:
	llm = get_llm()
	user_request = (state.get("user_request") or "").strip()
	execution_error = state.get("execution_error") or ""
	approved_code = state.get("approved_code") or ""
	current_result = state.get("execution_result") or {}
	schemas = state.get("multiple_csv_schemas") or {}

	next_node = decide_next_node(
		llm=llm,
		user_request=user_request,
		execution_error=execution_error,
		approved_code=approved_code,
		current_result=current_result,
		schemas=schemas,
	)
	if next_node == "direct_answer":
		response = answer_directly(
			llm=llm,
			user_request=user_request,
			execution_error=execution_error,
			current_result=current_result,
			schemas=schemas,
		)
		state = {**state, "next_node": next_node, "supervisor_response": response}
		if response:
			state = _append_history(state, "assistant", response)
		return state
	return {**state, "next_node": next_node}


def code_generator_node(state: AgentState) -> AgentState:
	llm = get_code_llm()
	user_request = (state.get("user_request") or "").strip()
	schemas = state.get("multiple_csv_schemas") or {}
	if not user_request:
		return state

	generated = generate_code(llm, user_request, schemas)
	state = {**state, "generated_code": generated}
	state = _append_history(state, "assistant", "Đã tạo mã. Vui lòng kiểm tra và phê duyệt trước khi thực thi.")
	return state


def human_approval_node(state: AgentState) -> AgentState:
	return state


def tool_executor_node(state: AgentState) -> AgentState:
	approved_code = (state.get("approved_code") or "").strip()
	schemas = state.get("multiple_csv_schemas") or {}
	if not approved_code:
		state = _append_history(
			state,
			"assistant",
			"Bạn cần phê duyệt mã trước khi thực thi. Bạn muốn tạo lại mã hay điều chỉnh yêu cầu?",
		)
		return {**state, "execution_error": "Bạn cần phê duyệt mã trước khi thực thi."}

	try:
		tables, df, default_table = load_tables_from_schemas(schemas)
	except Exception as e:
		state = _append_history(
			state,
			"assistant",
			"Không thể tải dữ liệu. Bạn muốn tạo lại mã hay điều chỉnh yêu cầu?",
		)
		return {**state, "execution_error": f"Lỗi tải dữ liệu: {e}"}

	try:
		result = safe_exec_analysis(approved_code, df, tables, default_table, schemas)
		return {**state, "execution_result": result, "execution_error": ""}
	except Exception as e:
		err_msg = build_error_message(e)
		_trace = build_error_traceback()
		state = _append_history(
			state,
			"assistant",
			"Thực thi thất bại. Bạn muốn tạo lại mã hay điều chỉnh yêu cầu?",
		)
		return {**state, "execution_error": err_msg, "_traceback": _trace}


def analyst_node(state: AgentState) -> AgentState:
	llm = get_llm()
	user_request = (state.get("user_request") or "").strip()
	schemas = state.get("multiple_csv_schemas") or {}
	result = state.get("execution_result") or {}
	insights = create_insights(llm, user_request, schemas, result)
	state = {**state, "insights": insights}
	if insights:
		state = _append_history(state, "assistant", insights)
	return state


def supervisor_review_node(state: AgentState) -> AgentState:
	llm = get_llm()
	try:
		observation = review_subagent_outputs(
			llm=llm,
			user_request=(state.get("user_request") or "").strip(),
			generated_code=state.get("generated_code") or "",
			execution_result=state.get("execution_result") or {},
			execution_error=state.get("execution_error") or "",
			insights=state.get("insights") or "",
		)
	except Exception as e:
		observation = f"Supervisor không thể tổng hợp thêm do lỗi: {e}"
	state = {**state, "supervisor_observation": observation, "next_node": "end"}
	if observation:
		state = _append_history(state, "assistant", observation)
	return state


def route_from_supervisor(state: AgentState) -> str:
	next_node = state.get("next_node") or "code_generator"
	if next_node == "tool_executor" and not (state.get("approved_code") or "").strip():
		return "code_generator"
	if next_node == "direct_answer":
		return END
	if next_node == "tool_executor":
		return "tool_executor"
	if next_node == "end":
		return END
	return "code_generator"


def route_after_execute(state: AgentState) -> str:
	if state.get("execution_error"):
		return "supervisor_review"
	return "analyst"


def route_after_analyst(state: AgentState) -> str:
	return "supervisor_review"


def build_graph(db_path: Optional[Path] = None) -> GraphArtifacts:
	base_dir = Path(__file__).parent
	db_path = db_path or (base_dir / "logs.db")

	builder = StateGraph(AgentState)
	builder.add_node("supervisor", supervisor_node)
	builder.add_node("code_generator", code_generator_node)
	builder.add_node("human_approval", human_approval_node)
	builder.add_node("tool_executor", tool_executor_node)
	builder.add_node("analyst", analyst_node)
	builder.add_node("supervisor_review", supervisor_review_node)

	builder.add_edge(START, "supervisor")
	builder.add_conditional_edges("supervisor", route_from_supervisor)
	builder.add_edge("code_generator", "human_approval")
	builder.add_edge("human_approval", "tool_executor")
	builder.add_conditional_edges("tool_executor", route_after_execute)
	builder.add_conditional_edges("analyst", route_after_analyst)
	builder.add_edge("supervisor_review", END)

	checkpointer = MemorySaver()
	graph = builder.compile(checkpointer=checkpointer, interrupt_before=["tool_executor"])

	return GraphArtifacts(graph=graph, checkpointer=checkpointer, db_path=db_path)
