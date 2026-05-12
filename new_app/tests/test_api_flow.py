from __future__ import annotations

import asyncio

import backend.main as main_module
from backend.main import ChatRequest, chat


class _Snap:
	def __init__(self, values=None, next_nodes=()):
		self.values = values or {}
		self.next = next_nodes


class _FakeGraph:
	def __init__(self):
		self.updated_as_node = None
		self.updated_payload = None
		self.invoked_payload = None

	def get_state(self, config):
		return _Snap(
			values={
				"session_id": "s1",
				"chat_history": [{"role": "assistant", "content": "Đã tạo mã."}],
				"multiple_csv_schemas": {"tables": {"sales": {}}},
				"generated_code": "result = {'summary': 'cũ'}",
				"approved_code": "",
			},
			next_nodes=("tool_executor",),
		)

	def update_state(self, config, payload, as_node=None):
		self.updated_payload = payload
		self.updated_as_node = as_node

	def invoke(self, payload, config=None):
		assert payload is not None
		self.invoked_payload = payload
		return {
			**payload,
			"generated_code": "result = {'summary': 'mới'}",
			"chat_history": payload["chat_history"]
			+ [{"role": "assistant", "content": "Đã tạo mã mới."}],
		}


def test_chat_invokes_graph_with_real_input_when_session_is_waiting_for_approval(monkeypatch):
	fake_graph = _FakeGraph()
	monkeypatch.setattr(main_module, "graph", fake_graph)
	monkeypatch.setattr(main_module, "save_session", lambda *args, **kwargs: None)
	monkeypatch.setattr(main_module, "insert_log", lambda *args, **kwargs: None)

	resp = asyncio.run(chat(ChatRequest(session_id="s1", user_request="phân tích lại", uploaded_files={})))

	assert fake_graph.updated_as_node is None
	assert fake_graph.updated_payload is None
	assert fake_graph.invoked_payload["user_request"] == "phân tích lại"
	assert fake_graph.invoked_payload["approved_code"] == ""
	assert fake_graph.invoked_payload["execution_error"] == ""
	assert resp.generated_code == "result = {'summary': 'mới'}"
	assert resp.chat_history[-1]["content"] == "Đã tạo mã mới."
