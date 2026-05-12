from __future__ import annotations

import ast
import json
from typing import Any, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.utils.json_utils import strip_code_fence

# =====================================================================
# 1. CẨM NANG NGHIỆP VỤ (DOMAIN RECIPES) CHO AGENT
# =====================================================================
DOMAIN_RECIPES = """
### CẨM NANG NGHIỆP VỤ (Hãy áp dụng nếu schema và yêu cầu phù hợp):

1. MẢNG BÁN HÀNG / TÀI CHÍNH (Có các cột Date, Revenue, COGS...):
- Tổng quan: Parse datetime, đếm số ngày (nunique), tìm min/max date.
- Tính toán: Gross_Profit = Revenue - COGS. Trích xuất Year, Month từ Date.
- Phân tích Top/Bottom: 
  + Năm doanh thu cao nhất: Groupby Year -> sum.
  + Tháng lọt top 3 nhiều nhất: Groupby [Year, Month] -> nlargest(3) -> value_counts(). 
  + QUAN TRỌNG: Khi trình bày kết quả này trong summary, hãy dùng vòng lặp hoặc list comprehension 
    để tạo danh sách Markdown (ví dụ: "* Tháng X: Y lần") thay vì dùng hàm .to_string().
  + Tháng có biên lợi nhuận thấp nhất: Tổng Gross_Profit theo tháng / Tổng Revenue theo tháng -> idxmin().
- Biểu đồ Time Series: resample theo 'ME' (Month End) và tính tổng để vẽ line chart gồm Revenue, COGS, Gross Profit.

2. MẢNG BẤT ĐỘNG SẢN (Có các cột price, area, ppm2, district, legal...):
- Xử lý giá trị: Cột 'price' thường có NaN. Hãy dùng `fillna(0)` trước khi aggregation.
- Top N: Sau khi `value_counts()` hoặc `groupby`, hãy đảm bảo kết quả không chứa NaN trước khi đưa vào `result['tables']`.
- Bước 1 (Tổng quan): Lấy shape, mô tả cơ bản (giá max/min, diện tích max/min). Chú ý: Cột 'price' thường tính bằng Tỷ VNĐ.
- Bước 2 (Phân tích khu vực): Groupby 'district' -> size() -> Lấy Top N lớn nhất -> Vẽ Bar chart.
- Bước 3 (Phân tích đơn giá): Groupby 'district' lấy mean của 'ppm2'. Vẽ Boxplot hoặc Bar chart để so sánh đơn giá giữa các quận trung tâm và ven.
- Bước 4 (Tương quan): Vẽ Scatter plot giữa 'area' (trục X) và 'price' (trục Y). Lưu ý các điểm ngoại lai (diện tích nhỏ nhưng giá cao).
- Bước 5 (Lọc cơ hội): Dùng df.loc[] để lọc. VD: district chứa 'Bình Thạnh', price < 10, area > 60, và (has_pink_book == 1 hoặc legal chứa 'Sổ hồng'). Gắn df kết quả vào list 'tables' của biến result.
"""

# =====================================================================
# 2. CORE LOGIC VÀ VALIDATION
# =====================================================================
def extract_json_from_text(text: Any) -> dict:
    """Hàm bọc thép: Tìm và trích xuất block JSON từ văn bản lộn xộn (Hỗ trợ cả List content từ Gemini)."""
    
    # Bước 1: Ép kiểu an toàn về chuỗi (String)
    if isinstance(text, list):
        # Nếu LLM trả về list các block, gom toàn bộ phần 'text' lại
        text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in text)
    elif not isinstance(text, str):
        text = str(text or "")
        
    text = text.strip()
    
    # Bước 2: Tìm và parse JSON
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and start_idx <= end_idx:
        json_str = text[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # ✅ Log error thay vì im lặng
            print(f"⚠️ JSON parse failed: {e}\nRaw: {json_str[:200]}")
            
    # ❌ Fallback này không an toàn - return {} sẽ dẫn đến code trống
    # Nên raise exception thay vì return {}
    raise ValueError(f"Cannot extract JSON from response: {text[:500]}")

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
    banned_names = {"open", "exec", "eval", "compile", "__import__", "input"}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "result":
                    has_result_assignment = True
        if isinstance(node, ast.Name) and node.id in banned_names:
            errors.append(f"Không được dùng builtin nguy hiểm: {node.id}.")

    if not has_result_assignment:
        errors.append("Phải gán biến result dạng dict: {'summary': str, 'tables': list, 'figures': list, 'used_tables': list}")
    return errors
def _build_generation_messages(user_request: str, schemas: dict) -> list[Any]:
    sys_prompt = SystemMessage(
        content=(
            "Bạn là Data Scientist Agent chuyên viết mã Python (Pandas, Matplotlib/Seaborn). "
            "Nhiệm vụ: Phân tích yêu cầu, áp dụng CẨM NANG NGHIỆP VỤ nếu phù hợp, và sinh mã chạy được.\n\n"
            f"{DOMAIN_RECIPES}\n\n"
            "QUY TẮC BẮT BUỘC: \n"
            "- Biến có sẵn: `tables` (dict[str, DataFrame]), `df` (DataFrame mặc định), `schemas` (dict), `pd`, `np`, `plt`, `sns`.\n"
            "- Xử lý an toàn: Kiểm tra cột tồn tại, dropna nếu cần thiết khi vẽ đồ thị.\n"
            "- Biểu đồ: Thêm `plt.tight_layout()`, nếu nhãn trục X dài thì xoay chữ (`plt.xticks(rotation=45)`).\n"
            "- Bạn PHẢI tạo biến `result` cuối cùng là một dictionary.\n\n"
            "⚠️ ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC LÀ JSON):\n"
            "Bạn PHẢI trả về một JSON có cấu trúc chính xác như sau (KHÔNG giải thích thêm):\n"
            "{\n"
            '  "thought_process": "Giải thích ngắn gọn logic",\n'
            '  "required_columns": ["Date", "Revenue"],\n'
            '  "generated_code": "import pandas as pd\\nimport matplotlib.pyplot as plt\\n...\\nfig, ax = plt.subplots()\\n...\\nresult = {\\\"summary\\\": \\\"Text insight\\\", \\\"tables\\\": [], \\\"figures\\\": [fig], \\\"used_tables\\\": []}"\n'
            "}\n\n"
            "🔴 LƯU Ý CỰC KỲ QUAN TRỌNG VỀ CODE:\n"
            "1. TUYỆT ĐỐI KHÔNG DÙNG `plt.savefig()`. Không lưu ảnh ra ổ cứng.\n"
            "2. Biến `result` BẮT BUỘC phải dùng đúng 4 keys: 'summary', 'tables', 'figures', 'used_tables'.\n"
            "3. Key 'figures' BẮT BUỘC phải chứa trực tiếp ĐỐI TƯỢNG `fig` của matplotlib (Ví dụ: `[fig]`), KHÔNG được chứa đường dẫn string."
        )
    )

    human = HumanMessage(
        content=(f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\nSCHEMA CÁC BẢNG:\n{schemas}\n")
    )
    return [sys_prompt, human]
def repair_code(llm: ChatOpenAI, code: str, user_request: str, schemas: dict, errors: List[str]) -> str:
    sys_prompt = SystemMessage(
        content=("Bạn là agent sửa mã Python. Sửa code để vượt qua kiểm tra tĩnh và đảm bảo biến `result` được gán. Trả về mã Python trực tiếp.")
    )
    human = HumanMessage(
        content=(f"YÊU CẦU NGƯỜI DÙNG:\n{user_request}\n\nSCHEMA:\n{schemas}\n\nLỖI CẦN SỬA:\n{errors}\n\nCODE HIỆN TẠI:\n```python\n{code}\n```\n")
    )
    resp = llm.invoke([sys_prompt, human])
    return strip_code_fence(resp.content or "")

def generate_code(llm: ChatOpenAI, user_request: str, schemas: dict, max_repair_attempts: int = 2) -> str:
    try:
        # Bỏ with_structured_output, dùng invoke thường để lấy Raw Text
        resp = llm.invoke(_build_generation_messages(user_request, schemas))
        raw_content = resp.content or ""
        
        # Dùng hàm trích xuất JSON bọc thép
        parsed_data = extract_json_from_text(raw_content)
        
        # Lấy code ra, nếu không parse được JSON thì dùng fallback quét Markdown code block
        generated_code = parsed_data.get("generated_code", "")
        if not generated_code or not generated_code.strip():
            error_text = "LLM không sinh code hợp lệ. Response: " + raw_content[:200]
            raise ValueError(error_text)
            
    except Exception as e:
        return f"result = {{\n    'summary': 'Lỗi kết nối LLM: {str(e)}',\n    'tables': [],\n    'figures': [],\n    'used_tables': []\n}}"

    # Kiểm tra lỗi
    errors = validate_generated_code(generated_code)
    attempt = 0
    
    # Sửa lỗi tự động nếu có
    while errors and attempt < max_repair_attempts:
        generated_code = repair_code(llm, generated_code, user_request, schemas, errors)
        errors = validate_generated_code(generated_code)
        attempt += 1
        
    if errors:
        error_text = "; ".join(errors)
        return (
            "result = {\n"
            f"    'summary': {('Không thể tự động sửa mã hợp lệ: ' + error_text)!r},\n"
            "    'tables': [],\n"
            "    'figures': [],\n"
            "    'used_tables': [],\n"
            "}\n"
        )
        
    return generated_code