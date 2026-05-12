from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.utils.json_utils import json_dumps, safe_json_loads


def summarize_execution_for_supervisor(result: Dict[str, Any]) -> Dict[str, Any]:
	if not isinstance(result, dict):
		return {}
	tables = []
	for table in (result.get("tables") or [])[:3]:
		if isinstance(table, dict) and table.get("type") == "dataframe":
			tables.append(
				{
					"type": "dataframe",
					"columns": table.get("columns", []),
					"rows": (table.get("data") or [])[:5],
				}
			)
		elif isinstance(table, dict):
			tables.append({k: v for k, v in table.items() if k != "data"})
		else:
			tables.append(str(table)[:500])
	return {
		"summary": result.get("summary", ""),
		"stdout": str(result.get("stdout", ""))[:1200],
		"tables": tables,
		"chart_count": len(result.get("images_base64_png") or []),
		"meta": result.get("meta", {}),
	}


def decide_next_node(
	llm: ChatOpenAI,
	user_request: str,
	execution_error: str,
	approved_code: str,
	current_result: Dict[str, Any],
	schemas: Dict[str, Any],
) -> str:
	"""Quyet dinh node tiep theo dua tren ngu canh hien tai."""

	if execution_error:
		return "direct_answer"

	sys_prompt = SystemMessage(
		content=(
			"Bạn là Supervisor trong hệ thống phân tích dữ liệu. "
			"Hãy làm rõ ý định, đánh giá ngữ cảnh, rồi chọn bước tiếp theo. "
			"Trả về JSON đúng định dạng: {\"next_node\": \"code_generator\"} hoặc "
			"{\"next_node\": \"tool_executor\"} hoặc {\"next_node\": \"direct_answer\"} hoặc {\"next_node\": \"end\"}. "
			"Quy tắc: \n"
			"- Nếu cần phân tích dữ liệu, vẽ biểu đồ, tính toán, hoặc cần code: chọn code_generator.\n"
			"- Nếu đã có mã được phê duyệt và người dùng muốn chạy: chọn tool_executor.\n"
			"- Nếu là câu hỏi đơn giản, hỏi đáp bình thường, giải thích hệ thống, hoặc lỗi cần hướng dẫn: chọn direct_answer.\n"
			"- Nếu không rõ, chọn code_generator.\n"
			"Chỉ trả về JSON, không viết thêm."
		)
	)

	human = HumanMessage(
		content=(
			f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
			f"ĐÃ CÓ MÃ PHÊ DUYỆT: {'CO' if approved_code else 'KHONG'}\n\n"
			f"KẾT QUẢ HIỆN TẠI (nếu có): {current_result}\n\n"
			f"SCHEMA CÁC BẢNG:\n{schemas}\n"
		)
	)

	try:
		resp = llm.invoke([sys_prompt, human])
		parsed = safe_json_loads(resp.content or "")
		next_node = str(parsed.get("next_node", "")).strip()
		if next_node not in {"code_generator", "tool_executor", "direct_answer", "end"}:
			next_node = "code_generator"
	except Exception:
		next_node = "code_generator"

	if next_node == "tool_executor" and not approved_code:
		next_node = "code_generator"

	return next_node


def answer_directly(
	llm: ChatOpenAI,
	user_request: str,
	execution_error: str,
	current_result: Dict[str, Any],
	schemas: Dict[str, Any],
) -> str:
	sys_prompt = SystemMessage(
		content=(
			"Bạn là Supervisor. Trả lời trực tiếp bằng TIẾNG VIỆT, rõ ràng và ngắn gọn. "
			"Nếu có lỗi thực thi, giải thích nguyên nhân có thể và đề xuất bước tiếp theo. "
			"Nếu người dùng hỏi chung, trả lời như trợ lý của nền tảng phân tích dữ liệu."
		)
	)
	human = HumanMessage(
		content=(
			f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
			f"LỖI THỰC THI (nếu có):\n{execution_error}\n\n"
			f"KẾT QUẢ HIỆN TẠI:\n{json_dumps(current_result)}\n\n"
			f"SCHEMA CÁC BẢNG:\n{json_dumps(schemas)}\n"
		)
	)
	resp = llm.invoke([sys_prompt, human])
	return (resp.content or "").strip()


def review_subagent_outputs(
	llm: ChatOpenAI,
	user_request: str,
	generated_code: str,
	execution_result: Dict[str, Any],
	execution_error: str,
	insights: str,
) -> str:
	sys_prompt = SystemMessage(
		content=(
			"Bạn là Supervisor. Hãy quan sát output của các agent con và kết luận trạng thái cuối cùng "
			"bằng TIẾNG VIỆT. Không lặp lại toàn bộ insight; chỉ tóm tắt ngắn gọn việc đã làm, "
			"nêu lỗi nếu có, và đề xuất bước tiếp theo nếu cần."
		)
	)
	human = HumanMessage(
		content=(
			f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
			f"CÓ MÃ ĐÃ SINH: {'CO' if generated_code else 'KHONG'}\n\n"
			f"LỖI THỰC THI:\n{execution_error}\n\n"
			f"KẾT QUẢ THỰC THI:\n{json_dumps(summarize_execution_for_supervisor(execution_result))}\n\n"
			f"INSIGHT ANALYST:\n{insights}\n"
		)
	)
	resp = llm.invoke([sys_prompt, human])
	return (resp.content or "").strip()
