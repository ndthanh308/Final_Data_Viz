from __future__ import annotations

from backend.agents.supervisor import summarize_execution_for_supervisor
from backend.graph import build_graph, route_after_execute, route_from_supervisor
import backend.graph as graph_module


class _FakeLLM:
	pass


def _patch_agents(monkeypatch):
	def fake_decide_next_node(**kwargs):
		return "code_generator"

	def fake_generate_code(llm, user_request, schemas):
		return (
			"result = {"
			f"'summary': 'mã cho {user_request}', "
			"'tables': [], 'figures': [], 'used_tables': []"
			"}"
		)

	def fake_create_insights(llm, user_request, schemas, result):
		return "nhận định"

	def fake_answer_directly(llm, user_request, execution_error, current_result, schemas):
		return f"trả lời trực tiếp: {user_request}"

	def fake_review_outputs(llm, user_request, generated_code, execution_result, execution_error, insights):
		if execution_error:
			return f"supervisor thấy lỗi: {execution_error}"
		return f"supervisor đã quan sát: {insights or execution_result.get('summary', '')}"

	monkeypatch.setattr(graph_module, "get_llm", lambda: _FakeLLM())
	monkeypatch.setattr(graph_module, "decide_next_node", fake_decide_next_node)
	monkeypatch.setattr(graph_module, "generate_code", fake_generate_code)
	monkeypatch.setattr(graph_module, "create_insights", fake_create_insights)
	monkeypatch.setattr(graph_module, "answer_directly", fake_answer_directly)
	monkeypatch.setattr(graph_module, "review_subagent_outputs", fake_review_outputs)


def test_execution_error_stops_and_returns_to_frontend():
	assert route_after_execute({"execution_error": "lỗi"}) == "supervisor_review"
	assert route_after_execute({"execution_error": ""}) == "analyst"


def test_supervisor_direct_answer_ends_turn(monkeypatch):
	_patch_agents(monkeypatch)
	monkeypatch.setattr(graph_module, "decide_next_node", lambda **kwargs: "direct_answer")
	artifacts = build_graph()
	graph = artifacts.graph
	config = {"configurable": {"thread_id": "test-direct-answer"}}
	state = {
		"session_id": "test-direct-answer",
		"chat_history": [{"role": "user", "content": "bạn là ai"}],
		"multiple_csv_schemas": {},
		"user_request": "bạn là ai",
		"generated_code": "",
		"approved_code": "",
		"execution_result": {},
		"execution_error": "",
		"insights": "",
		"next_node": "",
	}

	out = graph.invoke(state, config=config)

	assert out["supervisor_response"] == "trả lời trực tiếp: bạn là ai"
	assert out["chat_history"][-1]["content"] == "trả lời trực tiếp: bạn là ai"
	assert graph.get_state(config).next == ()


def test_supervisor_route_supports_direct_answer():
	assert route_from_supervisor({"next_node": "direct_answer"}) == "__end__"


def test_supervisor_execution_summary_omits_base64_images():
	summary = summarize_execution_for_supervisor(
		{
			"summary": "ok",
			"stdout": "x" * 2000,
			"images_base64_png": ["abc" * 1000, "def" * 1000],
			"tables": [
				{
					"type": "dataframe",
					"columns": ["a"],
					"data": [{"a": i} for i in range(10)],
				}
			],
			"meta": {"used_tables": ["sales"]},
		}
	)

	assert summary["chart_count"] == 2
	assert "images_base64_png" not in summary
	assert len(summary["stdout"]) == 1200
	assert len(summary["tables"][0]["rows"]) == 5


def test_supervisor_observes_outputs_after_analyst(monkeypatch):
	_patch_agents(monkeypatch)
	monkeypatch.setattr(graph_module, "decide_next_node", lambda **kwargs: "tool_executor")
	monkeypatch.setattr(
		graph_module,
		"load_tables_from_schemas",
		lambda schemas: ({"sales": object()}, object(), "sales"),
	)
	monkeypatch.setattr(
		graph_module,
		"safe_exec_analysis",
		lambda code, df, tables, default_table, schemas: {"summary": "chạy xong", "tables": []},
	)
	artifacts = build_graph()
	graph = artifacts.graph
	config = {"configurable": {"thread_id": "test-supervisor-observe"}}
	state = {
		"session_id": "test-supervisor-observe",
		"chat_history": [{"role": "user", "content": "chạy mã"}],
		"multiple_csv_schemas": {"tables": {"sales": {}}},
		"user_request": "chạy mã",
		"generated_code": "result = {}",
		"approved_code": "result = {}",
		"execution_result": {},
		"execution_error": "",
		"insights": "",
		"next_node": "",
	}

	first = graph.invoke(state, config=config)
	assert graph.get_state(config).next == ("tool_executor",)
	graph.update_state(config, {"approved_code": "result = {}"})
	out = graph.invoke(None, config=config)

	assert out["insights"] == "nhận định"
	assert out["supervisor_observation"] == "supervisor đã quan sát: nhận định"
	assert out["chat_history"][-1]["content"] == "supervisor đã quan sát: nhận định"


def test_supervisor_review_failure_does_not_break_execute(monkeypatch):
	_patch_agents(monkeypatch)
	monkeypatch.setattr(graph_module, "decide_next_node", lambda **kwargs: "tool_executor")
	monkeypatch.setattr(
		graph_module,
		"load_tables_from_schemas",
		lambda schemas: ({"sales": object()}, object(), "sales"),
	)
	monkeypatch.setattr(
		graph_module,
		"safe_exec_analysis",
		lambda code, df, tables, default_table, schemas: {"summary": "chạy xong", "tables": []},
	)
	monkeypatch.setattr(
		graph_module,
		"review_subagent_outputs",
		lambda **kwargs: (_ for _ in ()).throw(RuntimeError("review lỗi")),
	)
	artifacts = build_graph()
	graph = artifacts.graph
	config = {"configurable": {"thread_id": "test-review-fallback"}}
	state = {
		"session_id": "test-review-fallback",
		"chat_history": [{"role": "user", "content": "chạy mã"}],
		"multiple_csv_schemas": {"tables": {"sales": {}}},
		"user_request": "chạy mã",
		"generated_code": "result = {}",
		"approved_code": "result = {}",
		"execution_result": {},
		"execution_error": "",
		"insights": "",
		"next_node": "",
	}

	graph.invoke(state, config=config)
	graph.update_state(config, {"approved_code": "result = {}"})
	out = graph.invoke(None, config=config)

	assert out["execution_error"] == ""
	assert out["execution_result"]["summary"] == "chạy xong"
	assert out["supervisor_observation"] == "Supervisor không thể tổng hợp thêm do lỗi: review lỗi"


def test_chat_can_continue_from_human_approval_breakpoint(monkeypatch):
	_patch_agents(monkeypatch)
	artifacts = build_graph()
	graph = artifacts.graph
	config = {"configurable": {"thread_id": "test-chat-continue"}}
	initial_state = {
		"session_id": "test-chat-continue",
		"chat_history": [{"role": "user", "content": "yêu cầu đầu"}],
		"multiple_csv_schemas": {},
		"user_request": "yêu cầu đầu",
		"generated_code": "",
		"approved_code": "",
		"execution_result": {},
		"execution_error": "",
		"insights": "",
		"next_node": "",
	}

	first = graph.invoke(initial_state, config=config)
	assert "yêu cầu đầu" in first["generated_code"]
	assert graph.get_state(config).next == ("tool_executor",)

	second_payload = {
		**first,
		"user_request": "yêu cầu mới",
		"approved_code": "",
		"execution_error": "",
		"next_node": "",
		"chat_history": first["chat_history"] + [{"role": "user", "content": "yêu cầu mới"}],
	}
	graph.update_state(config, second_payload, as_node="supervisor")
	second = graph.invoke(None, config=config)

	assert "yêu cầu mới" in second["generated_code"]
	assert graph.get_state(config).next == ("tool_executor",)


def test_chat_can_continue_with_real_payload_not_null_from_human_approval_breakpoint(monkeypatch):
	_patch_agents(monkeypatch)
	artifacts = build_graph()
	graph = artifacts.graph
	config = {"configurable": {"thread_id": "test-chat-real-payload"}}
	initial_state = {
		"session_id": "test-chat-real-payload",
		"chat_history": [{"role": "user", "content": "yêu cầu đầu"}],
		"multiple_csv_schemas": {},
		"user_request": "yêu cầu đầu",
		"generated_code": "",
		"approved_code": "",
		"execution_result": {},
		"execution_error": "",
		"insights": "",
		"next_node": "",
	}

	first = graph.invoke(initial_state, config=config)
	assert "yêu cầu đầu" in first["generated_code"]
	assert graph.get_state(config).next == ("tool_executor",)

	second_payload = {
		**first,
		"user_request": "yêu cầu thứ hai",
		"approved_code": "",
		"execution_error": "",
		"next_node": "",
		"chat_history": first["chat_history"] + [{"role": "user", "content": "yêu cầu thứ hai"}],
	}
	second = graph.invoke(second_payload, config=config)

	assert "yêu cầu thứ hai" in second["generated_code"]
	assert graph.get_state(config).next == ("tool_executor",)
