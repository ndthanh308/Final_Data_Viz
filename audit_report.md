# Báo cáo Rà soát Source Code – Đối chiếu REQUIREMENTS.md

> **Phạm vi rà soát:** `new_app/backend/` + `new_app/frontend/app.py`  
> **Cơ sở đối chiếu:** `REQUIREMENTS.md` (42 dòng)  
> **Ngày rà soát:** 2026-05-12

---

## Tóm tắt nhanh

| Nhóm yêu cầu | Trạng thái | Điểm quan trọng |
|---|---|---|
| I.1 – Ràng buộc dữ liệu | ⚠️ Không kiểm chứng được | Không có validation dữ liệu đầu vào |
| I.2 – Tiêu chí Dashboard | ✅ Một phần | Phụ thuộc nội dung thực tế, backend OK |
| II.1 – Vai trò và Môi trường | ✅ Đạt | Chạy local, AI chỉ sinh code |
| II.2 – Không thực thi ngầm | ⚠️ Một phần vấn đề | `approved_code` tự điền ngay, thiếu trạng thái hiển thị rõ |
| II.3 – Human-in-the-loop | 🔴 Lỗ hổng nghiêm trọng | Bypass được, không có trạng thái "Chờ duyệt" cứng |
| II.4.A – Frontend API | ✅ Đạt | Đủ 4 chức năng |
| II.4.B – API AI | ✅ Đạt | `/api/ai/chat` đúng vai trò |
| II.4.C – API Thực thi | ⚠️ Một phần | Chưa tách biệt hoàn toàn logic |
| II.4.D – API Logs | ✅ Đạt | Đã tích hợp LangSmith Tracing & SQLite Logging |

---

## Chi tiết từng Tiêu chí

### I. YÊU CẦU VỀ ĐỒ ÁN TRỰC QUAN HÓA

#### I.1 – Ràng buộc Dữ liệu
> Dữ liệu thật, liên quan Việt Nam >50%, tối thiểu 7 biến + 2000 dòng.

**Trạng thái: ⚠️ Không kiểm chứng được trong code**

- Backend (`executor.py`) đọc file CSV bất kỳ, **không có bước validate** số dòng, số cột hay nguồn gốc dữ liệu.
- Frontend chỉ đọc schema preview 20 dòng — không kiểm tra `len(df) >= 2000` hay số lượng biến.
- **Vấn đề:** Hệ thống có thể chấp nhận bộ dữ liệu không đủ tiêu chí mà không cảnh báo.

**Khuyến nghị:** Thêm validation trong `_load_schema_preview()` hoặc `load_tables_from_schemas()`:
- Đọc hết file để đếm rows.
- Cảnh báo nếu `< 2000` dòng hoặc `< 7` cột.

---

#### I.2 – Tiêu chí Thiết kế Dashboard
> Độ tin cậy, đúng mục đích, rõ ràng, liên kết, tương tác, thẩm mỹ, chiều sâu phân tích, Tích hợp AI.

**Trạng thái: ✅ Backend đủ điều kiện — Frontend cơ bản**

- Backend trả đủ: biểu đồ (base64 PNG), bảng dữ liệu, insights từ Analyst.
- Frontend (`app.py`) dùng **Streamlit** — đủ hiển thị nhưng giao diện mặc định, không có thiết kế tùy chỉnh, không filter/tương tác nâng cao.
- **Lưu ý:** Streamlit không phải Dashboard framework chuyên dụng (Plotly Dash, Superset...). Tính "liên kết giữa các biểu đồ" và "điều hướng" rất hạn chế.

---

### II. YÊU CẦU TÍCH HỢP AI

#### II.1 – Vai trò và Môi trường
> Code chạy local, AI không tự thêm số liệu, con người ra quyết định.

**Trạng thái: ✅ Cơ bản đạt**

| Yêu cầu | Đánh giá |
|---|---|
| Chạy local | ✅ `executor.py` dùng `exec()` trực tiếp, đọc file từ `.hitl_sessions/` trên máy local |
| AI không tự thêm số liệu | ✅ `generate_code` chỉ sinh code, không inject data. System prompt cấm `requests`, `open` |
| Con người ra quyết định | ⚠️ Phụ thuộc vào HITL — xem phần II.3 |

---

#### II.2 – Nguyên tắc "Không thực thi ngầm" ⚠️
> Code AI phải được hiển thị rõ. Comment giải thích bằng ngôn ngữ tự nhiên trong code. AI không tự thay đổi dữ liệu gốc.

**Trạng thái: ⚠️ Đạt một phần — Còn 2 vấn đề**

✅ **Đã làm được:**
- Code AI được hiển thị trong `st.text_area` trước khi chạy.
- System prompt (`code_generator.py`, dòng 97) yêu cầu AI: `"Thêm comment TIẾNG VIỆT ngắn gọn trong code."`.
- `executor.py` không ghi đè file CSV gốc — dữ liệu chỉ đọc.

🔴 **Vấn đề 1 — Thiếu bắt buộc comment giải thích từng đoạn:**
```python
# code_generator.py, dòng 97
"- Thêm comment TIẾNG VIỆT ngắn gọn trong code.\n"
```
Chỉ là **khuyến khích** ("ngắn gọn") trong system prompt — AI có thể bỏ qua. REQUIREMENTS yêu cầu **bắt buộc** có comment kiểu `"Đoạn code này sẽ xóa 15 dòng..."`. Không có bước **validate** comment sau khi sinh code (hàm `validate_generated_code` không kiểm tra comment).

🔴 **Vấn đề 2 — `approved_code` tự điền ngay khi nhận code AI:**
```python
# frontend/app.py, dòng 152
def _queue_generated_code(state, generated_code):
    state["generated_code"] = generated_code or ""
    state["approved_code"] = generated_code or ""   # ← TỰ ĐIỀN LUÔN!
```
Điều này có nghĩa là ngay khi AI trả về code, `approved_code` đã có giá trị. Nếu người dùng nhấn "Phê duyệt và thực thi" mà không đọc, code vẫn chạy với **nội dung AI tạo ra gốc**. Về mặt triết lý, đây là pre-fill trước khi người dùng chủ động thay đổi.

---

#### II.3 – Human-in-the-loop (Cơ chế Phê duyệt) 🔴
> Code AI phải ở trạng thái "Chờ duyệt". Giao diện cho phép chỉnh sửa tham số. Chỉ khi con người bấm phê duyệt thì code mới chạy.

**Trạng thái: 🔴 Có lỗ hổng nghiêm trọng — Có thể bypass**

##### Phân tích luồng HITL thực tế:

```
[graph.py, dòng 249]
graph = builder.compile(checkpointer=checkpointer, interrupt_before=["tool_executor"])
```
✅ **Điểm tốt:** Graph được compile với `interrupt_before=["tool_executor"]` — khi code được sinh ra, graph **dừng** trước khi chạy executor.

✅ **Điểm tốt:** Backend `/api/ai/execute` kiểm tra `snap.next == ("tool_executor",)` — nếu không ở đúng trạng thái sẽ báo lỗi 400.

🔴 **Lỗ hổng 1 — Không có trạng thái "Chờ duyệt" hiển thị rõ trên UI:**
- Frontend **không hiển thị badge/label** "⏳ Đang chờ phê duyệt" hay trạng thái pending.
- Người dùng chỉ thấy text area với code, không biết đây là trạng thái HITL bắt buộc hay tùy chọn.

🔴 **Lỗ hổng 2 — `approved_code` bị pre-populate (như đã phân tích ở II.2):**
```python
# Người dùng có thể nhấn "Phê duyệt và thực thi" ngay mà không cần đọc code
# vì approved_code đã = generated_code từ đầu
```

🔴 **Lỗ hổng 3 — Không có cơ chế "Từ chối" (Reject):**
- Giao diện chỉ có nút **"Phê duyệt và thực thi"**.
- Không có nút **"Từ chối / Yêu cầu sinh lại"** riêng biệt từ màn hình review code.
- Nút "Sinh lại mã" chỉ xuất hiện khi **đã có lỗi thực thi** (`_render_error_message`), không phải ở bước review code.

🔴 **Lỗ hổng 4 — Có thể gọi `/api/ai/execute` trực tiếp mà không qua UI:**
```python
# main.py, dòng 169
state = graph.invoke(None, config=config)
```
API không có authentication/rate limiting. Bất kỳ HTTP client nào cũng có thể gọi `/api/ai/execute` với `approved_code` tùy ý, bỏ qua bước review của người dùng.

---

#### II.4 – Kiến trúc Hệ thống: 3 APIs bắt buộc phân tách

##### A. Frontend (Giao diện)
> Nhận yêu cầu, xem & chỉnh sửa mã, phê duyệt mã, hiển thị kết quả.

**Trạng thái: ✅ Đạt đủ 4 chức năng**

| Chức năng | Implementation |
|---|---|
| Nhận yêu cầu | `st.chat_input()` → `_call_chat()` |
| Xem & chỉnh sửa mã | `st.text_area("Mã Python", ...)` |
| Phê duyệt mã | Nút "Phê duyệt và thực thi" → `_call_execute()` |
| Hiển thị kết quả | `_render_execution_result()`, `_render_result_message()` |

---

##### B. API AI (Bắt buộc)
> Tiếp nhận từ Frontend, gửi kèm ngữ cảnh cho AI, trả về code + giải thích.

**Trạng thái: ✅ Đạt**

```
POST /api/ai/chat
```
- Nhận: `session_id`, `user_request`, `uploaded_files` (schemas)
- Xử lý: LangGraph → supervisor → code_generator → human_approval (interrupt)
- Trả về: `generated_code`, `insights`, `supervisor_response`, `chat_history`

✅ Trả về cả **code** (`generated_code`) và **giải thích** (`supervisor_response`, `insights`).

⚠️ **Một điểm nhỏ:** `insights` được trả về trong `/api/ai/chat` nhưng insight thực sự chỉ sinh ra sau khi **execute** (node `analyst`). Khi mới chat, `insights` trong response là giá trị cũ từ session trước.

---

##### C. API Thực thi (Bắt buộc)
> Tiếp nhận mã đã chỉnh sửa + phê duyệt, chạy code trên dữ liệu local, trả về kết quả.

**Trạng thái: ⚠️ Đạt về chức năng, nhưng có vấn đề thiết kế**

```
POST /api/ai/execute
```
- Nhận: `session_id`, `approved_code`
- Xử lý: resume graph → `tool_executor` → `analyst` → `supervisor_review`
- Trả về: `execution_result`, `execution_error`, `insights`

⚠️ **Vấn đề thiết kế:** API này vừa **thực thi code** vừa **sinh insights (AI)** trong cùng một call. REQUIREMENTS yêu cầu API Thực thi chỉ "chạy code và thu thập kết quả". Việc sinh insights là nhiệm vụ của AI — nên thuộc về "API AI". Hai chức năng đang bị gộp.

⚠️ **Vấn đề dữ liệu:** `load_tables_from_schemas()` đọc file CSV từ `.hitl_sessions/{session_id}/`. Nếu session quá cũ hoặc file bị xóa, API trả lỗi 500. Không có cơ chế kiểm tra trước.

---

##### D. API Logs (Bắt buộc) + Lưu trữ
> Lưu toàn bộ lịch sử: yêu cầu, mã nguồn, kết quả, giải thích. Truy xuất được.

**Trạng thái: ✅ Đạt**

✅ **Backend & Cơ sở hạ tầng:**
- **LangSmith Tracing:** Đã cấu hình qua biến môi trường (`LANGSMITH_TRACING_V2=true`). Toàn bộ luồng LangGraph được trace chi tiết (input, output, nội bộ node).
- **SQLite Logging:** Backend có endpoint `/api/logs` và lưu vào `logs.db` qua hàm `insert_log()`.
- **Dữ liệu lưu trữ:** Lưu đầy đủ `user_request`, `generated_code`, `approved_code`, `execution_result`, `insights`.

⚠️ **Lưu ý về UI:**
- Hiện tại người dùng cuối truy xuất lịch sử chủ yếu qua tính năng "Tải phiên" bằng `session_id`.
- Mặc dù Backend đầy đủ, việc thiếu một "Bảng điều khiển Logs" trực quan trên Frontend cho người dùng không chuyên có thể là một điểm cải thiện UX, nhưng về mặt kỹ thuật và yêu cầu lưu trữ/truy xuất (cho kiểm tra/audit) thì đã đạt.

---

## Tổng hợp các vấn đề ưu tiên cao (Cần sửa)

| # | Vấn đề | File | Mức độ |
|---|---|---|---|
| 1 | `approved_code` tự điền = `generated_code` ngay khi nhận — phá vỡ tinh thần HITL | `frontend/app.py:152` | 🔴 Nghiêm trọng |
| 2 | Không có nút "Từ chối / Yêu cầu sinh lại" ở bước review code | `frontend/app.py:222-231` | 🔴 Nghiêm trọng |
| 3 | Không có label/trạng thái "Chờ duyệt" hiển thị rõ ràng trên UI | `frontend/app.py` | 🔴 Nghiêm trọng |
| 4 | Cải thiện UI truy xuất Logs/Lịch sử (hiện tại dùng session_id) | `frontend/app.py` | 🟡 Thấp |
| 5 | Không có validation dữ liệu (>=2000 dòng, >=7 biến, >=50% VN) | `executor.py`, `app.py` | 🟠 Cao |
| 6 | Code AI không được validate có đủ comment tiếng Việt giải thích | `code_generator.py` | 🟠 Trung bình |
| 7 | `insights` trả về trong `/api/ai/chat` là giá trị cũ | `main.py:137` | 🟡 Nhỏ |

---

## Những điểm source code đã làm TỐT

- ✅ **`interrupt_before=["tool_executor"]`** — đúng cơ chế LangGraph HITL
- ✅ **`validate_code()` trong `executor.py`** — kiểm tra AST trước khi `exec()`
- ✅ **Sandbox `exec_globals`** — giới hạn builtins, cấm import nguy hiểm  
- ✅ **3 API tách biệt về URL** — `/api/ai/chat`, `/api/ai/execute`, `/api/logs`
- ✅ **SQLite logging đầy đủ** — lưu cả request, code, approved_code, result, insights
- ✅ **`save_session` + `fetch_session`** — khôi phục được trạng thái HITL
- ✅ **`safe_exec_analysis`** — chạy trong môi trường giới hạn, redirect stdout
- ✅ **Comment tiếng Việt trong system prompt** được yêu cầu AI sinh ra
