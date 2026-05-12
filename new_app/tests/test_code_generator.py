from __future__ import annotations

from dataclasses import dataclass

from backend.agents.code_generator import generate_code, validate_generated_code


@dataclass
class _Response:
	content: str


class _FakeLLM:
	def __init__(self, responses):
		self.responses = list(responses)
		self.calls = 0

	def invoke(self, messages):
		self.calls += 1
		return _Response(self.responses.pop(0))


def test_validate_generated_code_rejects_unsafe_or_incomplete_code():
	errors = validate_generated_code("import os\nprint('x')")

	assert "Không được import module nguy hiểm: os." in errors
	assert "Phải gán biến result dạng dict." in errors


def test_generate_code_repairs_invalid_code_before_returning():
	llm = _FakeLLM(
		[
			'{"generated_code": "import os\\nprint(\\"x\\")"}',
			'{"generated_code": "bang = df.head(5)\\nresult = {\\"summary\\": \\"ok\\", \\"tables\\": [bang], \\"figures\\": [], \\"used_tables\\": []}"}',
		]
	)

	code = generate_code(llm, "xem 5 dòng đầu", {"tables": {"sales": {}}})

	assert llm.calls == 2
	assert "import os" not in code
	assert validate_generated_code(code) == []


def test_generate_code_returns_safe_fallback_when_repair_fails():
	llm = _FakeLLM(
		[
			'{"generated_code": "import os"}',
			'{"generated_code": "import os"}',
		]
	)

	code = generate_code(llm, "phân tích", {}, max_repair_attempts=1)

	assert "Không thể tạo mã hợp lệ tự động" in code
	assert validate_generated_code(code) == []
