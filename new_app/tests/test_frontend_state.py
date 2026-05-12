from __future__ import annotations

from frontend.app import _apply_pending_code_editor, _queue_generated_code


def test_queue_generated_code_does_not_write_widget_key_immediately():
	state = {"code_editor": "người dùng đang sửa"}

	_queue_generated_code(state, "result = {'summary': 'mới'}")

	assert state["generated_code"] == "result = {'summary': 'mới'}"
	assert state["approved_code"] == "result = {'summary': 'mới'}"
	assert state["pending_code_editor"] == "result = {'summary': 'mới'}"
	assert state["code_editor"] == "người dùng đang sửa"


def test_apply_pending_code_editor_writes_widget_key_before_render():
	state = {"pending_code_editor": "mã mới"}

	_apply_pending_code_editor(state)

	assert state["code_editor"] == "mã mới"
	assert state["pending_code_editor"] is None


def test_apply_pending_code_editor_noops_without_pending_value():
	state = {"code_editor": "mã hiện tại", "pending_code_editor": None}

	_apply_pending_code_editor(state)

	assert state["code_editor"] == "mã hiện tại"
