from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
	"""Tra ve thoi gian hien tai theo ISO (UTC)."""
	return datetime.now(timezone.utc).isoformat()
