from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.json_utils import json_dumps
from backend.utils.time_utils import utc_now_iso


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_sessions (
  session_id TEXT PRIMARY KEY,
  updated_at TEXT NOT NULL,
  state_json TEXT NOT NULL,
  chat_history_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  session_id TEXT NOT NULL,
  user_request TEXT,
  generated_code TEXT,
  approved_code TEXT,
  execution_result_json TEXT,
  execution_error TEXT,
  insights TEXT
);
"""


def init_db(db_path: Path) -> None:
	db_path.parent.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(db_path) as conn:
		conn.executescript(DB_SCHEMA)
		conn.commit()


def save_session(db_path: Path, session_id: str, state: Dict[str, Any]) -> None:
	init_db(db_path)
	chat_history = state.get("chat_history") or []
	payload = dict(state)
	payload["chat_history"] = chat_history
	with sqlite3.connect(db_path) as conn:
		conn.execute(
			"""
			INSERT INTO hitl_sessions (session_id, updated_at, state_json, chat_history_json)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(session_id) DO UPDATE SET
			  updated_at=excluded.updated_at,
			  state_json=excluded.state_json,
			  chat_history_json=excluded.chat_history_json
			""",
			(
				str(session_id),
				utc_now_iso(),
				json_dumps(payload),
				json_dumps(chat_history),
			),
		)
		conn.commit()


def fetch_session(db_path: Path, session_id: str) -> Optional[Dict[str, Any]]:
	init_db(db_path)
	with sqlite3.connect(db_path) as conn:
		conn.row_factory = sqlite3.Row
		row = conn.execute(
			"SELECT * FROM hitl_sessions WHERE session_id = ?",
			(str(session_id),),
		).fetchone()
	if not row:
		return None
	return {k: row[k] for k in row.keys()}


def insert_log(db_path: Path, state: Dict[str, Any]) -> None:
	init_db(db_path)
	with sqlite3.connect(db_path) as conn:
		conn.execute(
			"""
			INSERT INTO hitl_logs (
			  created_at, session_id, user_request,
			  generated_code, approved_code, execution_result_json,
			  execution_error, insights
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				utc_now_iso(),
				str(state.get("session_id", "")),
				str(state.get("user_request", "")),
				state.get("generated_code", ""),
				state.get("approved_code", ""),
				json_dumps(state.get("execution_result", {})),
				state.get("execution_error", ""),
				state.get("insights", ""),
			),
		)
		conn.commit()


def fetch_logs(db_path: Path, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
	init_db(db_path)
	with sqlite3.connect(db_path) as conn:
		conn.row_factory = sqlite3.Row
		if session_id:
			rows = conn.execute(
				"SELECT * FROM hitl_logs WHERE session_id = ? ORDER BY id DESC LIMIT ?",
				(str(session_id), int(limit)),
			).fetchall()
		else:
			rows = conn.execute(
				"SELECT * FROM hitl_logs ORDER BY id DESC LIMIT ?",
				(int(limit),),
			).fetchall()
	return [{k: r[k] for k in r.keys()} for r in rows]
