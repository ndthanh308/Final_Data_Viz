from __future__ import annotations

import ast
from typing import Any, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.utils.json_utils import safe_json_loads, strip_code_fence


def validate_generated_code(code: str) -> List[str]:
	errors: List[str] = []
	clean_code = strip_code_fence(code)
	if not clean_code.strip():
		return ["Mã rỗng."]
	try:
		tree = ast.parse(clean_code)
	except SyntaxError as e:
		return [f"Lỗi cú pháp dòng {e.lineno}: {e.msg}"]

	has_result_assignment = False
	banned_import_roots = {
		"os",
		"sys",
		"subprocess",
		"socket",
		"pathlib",
		"shutil",
		"requests",
		"http",
		"urllib",
		"ftplib",
		"paramiko",
		"shlex",
		"importlib",
		"builtins",
	}
	banned_names = {"open", "exec", "eval", "compile", "__import__", "input"}
	placeholder_words = {"YOUR_COLUMN", "TODO", "FIXME", "PLACEHOLDER"}

	for node in ast.walk(tree):
		if isinstance(node, ast.Assign):
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id == "result":
					has_result_assignment = True
		if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "result":
			has_result_assignment = True
		if isinstance(node, ast.Import):
			for alias in node.names:
				root = alias.name.split(".")[0]
				if root in banned_import_roots:
					errors.append(f"Không được import module nguy hiểm: {root}.")
		if isinstance(node, ast.ImportFrom):
			root = (node.module or "").split(".")[0]
			if node.level != 0 or root in banned_import_roots:
				errors.append(f"Không được import module nguy hiểm: {root}.")
		if isinstance(node, ast.Name) and node.id in banned_names:
			errors.append(f"Không được dùng builtin nguy hiểm: {node.id}.")

	for word in placeholder_words:
		if word in clean_code:
			errors.append(f"Không được để placeholder: {word}.")
	if not has_result_assignment:
		errors.append("Phải gán biến result dạng dict.")
	return errors


def _extract_generated_code(content: str) -> str:
	parsed = safe_json_loads(content or "")
	generated_code = (parsed.get("generated_code") or "").strip()
	if not generated_code:
		generated_code = (content or "").strip()
	return strip_code_fence(generated_code)


def _build_generation_messages(user_request: str, schemas: dict) -> list[Any]:
	sys_prompt = SystemMessage(
		content=(
			"Bạn là agent tạo mã Python chuyên phân tích dữ liệu. "
			"Nhiệm vụ: sinh code Pandas/Matplotlib chạy được trong môi trường đã có sẵn dữ liệu. "
			"Tuyệt đối KHÔNG thực thi code. "
			"Trả về JSON: {\"generated_code\": \"...\"}.\n"
			"Quy tắc bắt buộc: \n"
			"- Biến có sẵn: tables (dict[str, DataFrame]), df (DataFrame mặc định), schemas (dict), pd, np, plt, sns.\n"
			"- Không đọc file, không gọi mạng, không dùng open/eval/exec/subprocess/os/requests.\n"
			"- Được import thư viện phân tích an toàn nếu cần, nhưng ưu tiên biến có sẵn.\n"
			"- Biến có sẵn: tables (dict[str, DataFrame]), df (DataFrame mặc định), schemas (dict).\n"
			"- Không dùng placeholder (VD: YOUR_COLUMN, TODO).\n"
			"- Luôn kiểm tra bảng/cột tồn tại trước khi dùng; nếu thiếu cột thì tạo result giải thích thay vì raise lỗi.\n"
			"- Không định nghĩa lại require_columns hoặc pick_first_column.\n"
			"- Nhấn mạnh đồ thị dễ đọc: fig size rõ ràng, plt.tight_layout(), xoay nhãn khi cần, dùng bar ngang nếu nhãn bị chồng.\n"
			"- Xử lý dữ liệu bẩn: parse datetime, ép kiểu số, xử lý NaN, tránh lỗi với bảng rỗng.\n"
			"- Tạo biến result là dict có đúng các khóa: summary (str), tables (list), figures (list), used_tables (list[str]).\n"
			"- tables chỉ chứa DataFrame/dict/text ngắn; figures chứa các Figure đã tạo.\n"
			"- Code phải chạy được ngay cả khi dữ liệu thiếu cột mong muốn.\n"
			"- Thêm comment TIẾNG VIỆT ngắn gọn trong code.\n"
		)
	)

	human = HumanMessage(
		content=(
			f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
			f"SCHEMA CÁC BẢNG:\n{schemas}\n"
		)
	)
	return [sys_prompt, human]


def repair_code(llm: ChatOpenAI, code: str, user_request: str, schemas: dict, errors: List[str]) -> str:
	sys_prompt = SystemMessage(
		content=(
			"Bạn là agent sửa mã Python phân tích dữ liệu. "
			"Sửa code để vượt qua kiểm tra tĩnh và chạy an toàn hơn. "
			"Không đổi mục tiêu phân tích. Trả về JSON: {\"generated_code\": \"...\"}."
		)
	)
	human = HumanMessage(
		content=(
			f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\n"
			f"SCHEMA CÁC BẢNG:\n{schemas}\n\n"
			f"LỖI CẦN SỬA:\n{errors}\n\n"
			f"CODE HIỆN TẠI:\n```python\n{code}\n```\n"
		)
	)
	resp = llm.invoke([sys_prompt, human])
	return _extract_generated_code(resp.content or "")


def generate_code(llm: ChatOpenAI, user_request: str, schemas: dict, max_repair_attempts: int = 2) -> str:
	resp = llm.invoke(_build_generation_messages(user_request, schemas))
	generated_code = _extract_generated_code(resp.content or "")
	errors = validate_generated_code(generated_code)
	attempt = 0
	while errors and attempt < max_repair_attempts:
		generated_code = repair_code(llm, generated_code, user_request, schemas, errors)
		errors = validate_generated_code(generated_code)
		attempt += 1
	if errors:
		error_text = "; ".join(errors)
		return (
			"result = {\n"
			f"    'summary': {('Không thể tạo mã hợp lệ tự động: ' + error_text)!r},\n"
			"    'tables': [],\n"
			"    'figures': [],\n"
			"    'used_tables': [],\n"
			"}\n"
		)
	return generated_code
