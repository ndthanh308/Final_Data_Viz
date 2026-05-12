from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.utils.json_utils import json_dumps


def summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
	if not isinstance(result, dict):
		return {}
	summary = {
		"summary": result.get("summary", ""),
		"meta": result.get("meta", {}),
		"tables": [],
	}
	for t in (result.get("tables") or [])[:3]:
		if isinstance(t, dict) and t.get("type") == "dataframe":
			summary["tables"].append(
				{
					"columns": t.get("columns", []),
					"rows": (t.get("data", []) or [])[:5],
				}
			)
		else:
			summary["tables"].append(t)
	return summary


def create_insights(llm: ChatOpenAI, user_request: str, schemas: dict, result: Dict[str, Any]) -> str:
	if result:
		sys_prompt = SystemMessage(
			content=(
				"Bạn là Analyst. Hãy đưa ra nhận định/insight kinh doanh bằng TIẾNG VIỆT dựa trên kết quả đã thực thi. "
				"Trả lời rõ ràng, ngắn gọn, có thể gợi ý hành động."
			)
		)
		human = HumanMessage(
			content=(
				f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
				f"TÓM TẮT KẾT QUẢ:\n{json_dumps(summarize_result(result))}\n\n"
				f"SCHEMA CÁC BẢNG:\n{json_dumps(schemas)}\n"
			)
		)
	else:
		sys_prompt = SystemMessage(
			content=(
				"Bạn là Analyst. Hãy trả lời câu hỏi người dùng bằng TIẾNG VIỆT, "
				"nếu cần thiết thì đề xuất bước tiếp theo."
			)
		)
		human = HumanMessage(
			content=(
				f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
				f"SCHEMA CÁC BẢNG (nếu có):\n{json_dumps(schemas)}\n"
			)
		)

	resp = llm.invoke([sys_prompt, human])
	return (resp.content or "").strip()
