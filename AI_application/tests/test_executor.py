from __future__ import annotations

import pandas as pd
import pytest
from matplotlib import pyplot as plt

from backend.services.executor import load_tables_from_schemas, safe_exec_analysis


def _run(code: str):
	df = pd.DataFrame({"nhom": ["A", "A", "B"], "doanh_thu": [10, 15, 8]})
	return safe_exec_analysis(
		code=code,
		df=df,
		tables={"sales": df},
		default_table="sales",
		schemas={"tables": {"sales": {}}},
	)


def test_safe_exec_allows_common_analysis_imports_and_captures_outputs():
	result = _run(
		"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Gom nhóm doanh thu theo nhóm và vẽ biểu đồ.
bang = df.groupby("nhom", as_index=False)["doanh_thu"].sum()
fig = plt.figure(figsize=(4, 3))
plt.bar(bang["nhom"], bang["doanh_thu"])
plt.tight_layout()
print("Đã xử lý", len(bang), "nhóm")
result = {
    "summary": "Đã tổng hợp doanh thu theo nhóm.",
    "tables": [bang],
    "figures": [fig],
    "used_tables": ["sales"],
}
"""
	)

	assert result["summary"] == "Đã tổng hợp doanh thu theo nhóm."
	assert "Đã xử lý 2 nhóm" in result["stdout"]
	assert result["tables"][0]["type"] == "dataframe"
	assert result["images_base64_png"]
	assert result["meta"]["used_tables"] == ["sales"]


def test_safe_exec_strips_python_fence_before_running():
	result = _run(
		"""```python
bang = df.head(1)
result = {"summary": "ok", "tables": [bang], "figures": [], "used_tables": []}
```"""
	)

	assert result["summary"] == "ok"
	assert result["tables"][0]["data"][0]["nhom"] == "A"


def test_safe_exec_allows_globals_for_generated_code_compatibility():
	result = _run(
		"""
ngu_canh = globals()
bang = ngu_canh["df"].head(2)
result = {"summary": "globals ok", "tables": [bang], "figures": [], "used_tables": []}
"""
	)

	assert result["summary"] == "globals ok"
	assert len(result["tables"][0]["data"]) == 2


def test_safe_exec_allows_common_pandas_rename_and_replace():
	result = _run(
		"""
bang = df.rename(columns={"nhom": "phan_khuc"}).replace({"phan_khuc": {"A": "Nhóm A"}})
result = {"summary": "rename ok", "tables": [bang], "figures": [], "used_tables": []}
"""
	)

	assert result["summary"] == "rename ok"
	assert result["tables"][0]["columns"] == ["phan_khuc", "doanh_thu"]
	assert result["tables"][0]["data"][0]["phan_khuc"] == "Nhóm A"


def test_safe_exec_allows_time_import_for_timing_metadata():
	result = _run(
		"""
import time

bat_dau = time.time()
bang = df.head(1)
ket_thuc = time.time()
result = {
    "summary": f"Đã chạy trong {ket_thuc - bat_dau:.4f} giây",
    "tables": [bang],
    "figures": [],
    "used_tables": [],
}
"""
	)

	assert result["summary"].startswith("Đã chạy trong")
	assert result["tables"][0]["data"][0]["nhom"] == "A"


def test_safe_exec_allows_regular_standard_library_imports():
	result = _run(
		"""
import datetime
import json
import re

hom_nay = datetime.date(2024, 1, 2).isoformat()
payload = json.dumps({"ngay": hom_nay}, ensure_ascii=False)
hop_le = bool(re.search("2024", payload))
result = {"summary": f"stdlib ok: {hop_le}", "tables": [df.head(1)], "figures": [], "used_tables": []}
"""
	)

	assert result["summary"] == "stdlib ok: True"


def test_safe_exec_allows_pandas_private_attributes_when_user_approves_code():
	result = _run(
		"""
ten_lop = df.__class__.__name__
result = {"summary": ten_lop, "tables": [], "figures": [], "used_tables": []}
"""
	)

	assert result["summary"] == "DataFrame"


def test_safe_exec_starts_with_clean_matplotlib_state_for_datetime_plots():
	plt.figure()
	plt.plot(["A", "B"], [1, 2])

	result = _run(
		"""
bang = df.copy()
bang["ngay"] = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
fig = plt.figure(figsize=(4, 3))
plt.plot(bang["ngay"], bang["doanh_thu"], marker="o")
plt.tight_layout()
result = {"summary": "datetime ok", "tables": [bang], "figures": [fig], "used_tables": []}
"""
	)

	assert result["summary"] == "datetime ok"
	assert len(result["images_base64_png"]) == 1


@pytest.mark.parametrize(
	"code, message",
	[
		("import os\nresult = {}", "Không cho phép import 'os'"),
		("from subprocess import run\nresult = {}", "Không cho phép import 'subprocess'"),
		("open('x.txt', 'w')\nresult = {}", "Không được sử dụng 'open'"),
	],
)
def test_safe_exec_blocks_dangerous_code(code: str, message: str):
	with pytest.raises(ValueError, match=message):
		_run(code)


def test_load_tables_from_schemas_rejects_missing_context():
	with pytest.raises(ValueError, match="Cần có raw_dir"):
		load_tables_from_schemas({"tables": {}})
