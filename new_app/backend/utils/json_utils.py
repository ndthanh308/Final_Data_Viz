from __future__ import annotations

import json
import re
from typing import Any, Dict


def json_dumps(obj: Any) -> str:
	return json.dumps(obj, ensure_ascii=False, default=str)


def safe_json_loads(text: str) -> Dict[str, Any]:
	t = (text or "").strip()
	if t.startswith("```"):
		match = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.DOTALL | re.IGNORECASE)
		if match:
			t = match.group(1).strip()
	if not t.startswith("{"):
		match = re.search(r"\{.*\}", t, flags=re.DOTALL)
		if match:
			t = match.group(0)
	try:
		return json.loads(t)
	except Exception:
		return {}


def strip_code_fence(text: str) -> str:
	t = (text or "").strip()
	if not t.startswith("```"):
		return t
	match = re.search(r"```(?:python|py)?\s*(.*?)```", t, flags=re.DOTALL | re.IGNORECASE)
	if match:
		return match.group(1).strip()
	return t.strip("`").strip()
