# Nền tảng Phân tích Dữ liệu AI (HITL)

Hệ thống phân tích dữ liệu theo kiến trúc **Multi-Agent Supervisor** và **Human-in-the-loop**.
Toàn bộ giao diện, phản hồi API và phản hồi agent đều bằng tiếng Việt.

## Tính năng chính

- **Multi-Agent + Supervisor**: điều phối luồng (tạo mã / thực thi / tạo nhận định).
- **Human-in-the-loop**: mã chỉ chạy sau khi người dùng **phê duyệt**.
- **Nhiều CSV**: tải nhiều file, chọn bảng mặc định `df`, truy cập thêm qua `tables["ten_bang"]`.
- **Sandbox thực thi cục bộ**: chặn import/builtin nguy hiểm và không cho phép truy cập hệ thống/mạng.
- **Lưu phiên + log**: lưu trạng thái phiên vào SQLite để có thể tải lại.

## Cấu trúc thư mục

```
new_app/
├── backend/
│   ├── main.py                  # FastAPI endpoints
│   ├── graph.py                 # LangGraph workflow
│   ├── agents/                  # supervisor / code generator / analyst
│   ├── services/executor.py     # sandbox exec + kết quả (stdout/tables/charts)
│   ├── database/store.py        # SQLite lưu session + logs
│   └── utils/
├── frontend/
│   └── app.py                   # Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

## Yêu cầu

- Python khuyến nghị: **3.10+**
- OS: Linux/macOS/Windows đều chạy được (miễn là cài được dependencies).

## Cài đặt

```bash
cd new_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Cấu hình (.env)

Các biến môi trường thường dùng:

- `API_BASE` (frontend dùng): URL backend. Mặc định trong Streamlit là `http://127.0.0.1:8001`.
- `OPENAI_API_KEY`: hiện đang được kiểm tra bắt buộc trong backend (dù bạn dùng Gemini).
- `GOOGLE_API_KEY`: dùng cho Gemini (hiện tại `backend/graph.py` đang cấu hình `ChatGoogleGenerativeAI`).
- `OPENAI_MODEL`, `OPENAI_CODE_MODEL`: chỉ có ý nghĩa khi bạn cấu hình backend dùng OpenAI (ChatOpenAI).

Ví dụ `.env` tối thiểu để chạy theo cấu hình hiện tại:

```bash
OPENAI_API_KEY=...        # hiện đang bị kiểm tra bắt buộc
GOOGLE_API_KEY=...

# Backend URL mà frontend gọi tới
API_BASE=http://127.0.0.1:8001
```

## Chạy hệ thống

### 1) Chạy backend (FastAPI)

Khuyến nghị chạy ở cổng **8001** để khớp mặc định của frontend:

```bash
cd new_app
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Kiểm tra nhanh:

```bash
curl http://127.0.0.1:8001/health
```

### 2) Chạy frontend (Streamlit)

```bash
cd new_app
streamlit run frontend/app.py
```

Nếu backend không chạy ở `8001`, hãy đặt `API_BASE` trước khi chạy:

```bash
API_BASE=http://127.0.0.1:8001 streamlit run frontend/app.py
```

## Luồng sử dụng (HITL)

1. Tải nhiều file CSV trong UI.
2. Nhập yêu cầu phân tích (chat).
3. Hệ thống sinh **mã Python** (hiển thị để bạn sửa).
4. Bạn bấm **Phê duyệt và thực thi** → backend chạy trong sandbox.
5. UI hiển thị **bảng**, **biểu đồ**, và phần **nhận định/gợi ý**.

## API (backend)

Backend hiện cung cấp các endpoint chính:

- `POST /api/ai/chat`
	- Input: `session_id` (tuỳ chọn), `user_request`, `uploaded_files` (ngữ cảnh dữ liệu từ frontend).
	- Output: `generated_code` (nếu có), `chat_history`, `insights`, ...

- `POST /api/ai/execute`
	- Input: `session_id`, `approved_code`.
	- Output: `execution_result` (stdout / tables / images base64), `insights`, `execution_error`, ...

- `GET /api/sessions/{session_id}`: tải lại state + chat history từ SQLite.
- `GET /api/logs?limit=50&session_id=...`: xem log gần đây.
- `GET /health`: kiểm tra trạng thái + model đang cấu hình.

Ví dụ gọi nhanh:

```bash
curl -X POST http://127.0.0.1:8001/api/ai/chat \
	-H 'Content-Type: application/json' \
	-d '{"user_request":"Tóm tắt dữ liệu và vẽ biểu đồ phân phối", "uploaded_files":{}}'
```

## Dữ liệu nhiều CSV được truyền như thế nào?

Frontend sẽ lưu các CSV đã upload vào thư mục cục bộ:

- `.hitl_sessions/<session_id>/*.csv`

Sau đó gửi lên backend một ngữ cảnh dạng JSON (rút gọn):

```json
{
	"raw_dir": ".../.hitl_sessions/session-xxxx",
	"default_table": "sales",
	"tables": {
		"sales": {"columns": [...], "dtypes": {...}, "sample": [...], "preview": [...]}
	}
}
```

Backend dùng `raw_dir` để đọc lại CSV trong lúc thực thi.

## Hợp đồng thực thi mã (Sandbox)

### Biến có sẵn khi chạy code

Trong sandbox, code phân tích có thể dùng:

- `df`: DataFrame mặc định (bảng bạn chọn).
- `tables`: dict các bảng (`tables["ten_bang"]`).
- `schemas`: ngữ cảnh (raw_dir, default_table, thông tin cột/dtype/sample).
- thư viện: `pd`, (tuỳ môi trường) `np`, `plt`, `sns`.
- helper: `require_columns(df, [...])`, `pick_first_column(df, [...])`.

### Output bắt buộc

Code phải gán biến `result` là một `dict`. Khuyến nghị dùng cấu trúc:

```python
result = {
	"summary": "...",
	"tables": [df_ket_qua, {"k": "v"}, "text"],
	"figures": [fig],
	"used_tables": ["sales"],
}
```

Lưu ý:

- Backend sẽ tự thu thập biểu đồ từ Matplotlib (các figure đang mở) và trả về `images_base64_png`.
- Nếu `tables` chứa DataFrame, backend sẽ chuyển thành JSON (tối đa ~200 dòng đầu).

### Giới hạn bảo mật

- Chỉ chạy sau khi người dùng **phê duyệt**.
- Chặn import các module hệ thống/mạng (ví dụ: `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, ...).
- Chặn builtin nguy hiểm (ví dụ: `open`, `exec`, `eval`, `__import__`, `input`).

Nếu code cố import/ gọi các thành phần trên, backend sẽ trả về lỗi dạng “Không cho phép …”.

## Lưu trữ phiên và log

- SQLite được lưu mặc định tại: `backend/logs.db`
- Bảng `hitl_sessions`: lưu state + chat history để tải lại theo `session_id`.
- Bảng `hitl_logs`: lưu từng lượt xử lý (user_request, generated_code, execution_error, ...).

## Chạy test

```bash
cd new_app
pytest -q
```

## Troubleshooting nhanh

- **Frontend không kết nối được backend**: kiểm tra `API_BASE` và cổng uvicorn (khuyến nghị cả hai cùng `8001`).
- **Báo thiếu API key**: đảm bảo `.env` có `OPENAI_API_KEY` và `GOOGLE_API_KEY` (theo cấu hình hiện tại).
- **Lỗi “Không cho phép import …”**: sandbox đang chặn import hệ thống/mạng; hãy viết lại code chỉ dùng pandas/matplotlib/seaborn.
- **Lỗi “Không tạo được biến result”**: code phải gán `result` là `dict`.
- **Lỗi “Không tìm thấy CSV…”**: kiểm tra bạn đã upload CSV trong UI và `raw_dir` còn tồn tại.
