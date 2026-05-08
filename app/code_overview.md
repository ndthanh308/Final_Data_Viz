# Tổng Quan Code Thư Mục `app`

## 1. Mục đích của thư mục `app`

Thư mục `app` chứa toàn bộ phần ứng dụng chạy theo mô hình:

1. `Streamlit` làm giao diện để người dùng nhập yêu cầu và duyệt code AI sinh ra.
2. `FastAPI` làm backend API để nhận request từ giao diện.
3. `LangGraph` điều phối luồng Human-in-the-loop:
   - AI chỉ sinh code
   - người dùng xem/sửa/duyệt code
   - hệ thống mới thực thi code sau khi được duyệt

Nói ngắn gọn: đây là một hệ thống phân tích dữ liệu có AI hỗ trợ, nhưng quyền chạy code vẫn nằm ở người dùng.

## 2. Cấu trúc file trong `app`

### `app.py`
Giao diện `Streamlit` để test pipeline.

### `main.py`
Backend `FastAPI`, định nghĩa các API endpoint.

### `graph.py`
Phần lõi xử lý:
- sinh code bằng LLM
- chờ người dùng duyệt
- chạy code cục bộ
- ghi log

### `readme.md`
Ghi chú cách chạy nhanh ứng dụng.

### `prompt.md`
Prompt/spec gốc mô tả yêu cầu hệ thống cần xây.

### `logs.db`
SQLite database dùng để lưu lịch sử request, code, kết quả chạy.

### `__init__.py`
Đánh dấu `app` là một Python package.

### `__pycache__/`
File sinh tự động bởi Python, không phải logic chính của dự án.

## 3. Kiến trúc tổng thể

Luồng chạy chính:

1. Người dùng mở `Streamlit` trong `app.py`.
2. Chọn bảng dữ liệu CSV từ thư mục `data/main/raw`.
3. Nhập yêu cầu phân tích.
4. `app.py` gọi `POST /api/ai/generate` trong `main.py`.
5. `main.py` gọi graph trong `graph.py` để:
   - sinh code
   - dừng trước bước thực thi
6. Giao diện hiển thị code cho người dùng xem/sửa.
7. Người dùng bấm duyệt.
8. `app.py` gọi `POST /api/ai/execute`.
9. `main.py` tiếp tục graph:
   - nạp dữ liệu thật từ CSV
   - thực thi code đã được duyệt
   - gom kết quả bảng, biểu đồ, stdout
   - lưu log vào `logs.db`
10. `app.py` hiển thị kết quả lên giao diện.

Ngoài ra còn có một luồng phụ là `Chat mode`, dùng để hỏi đáp với AI mà không chạy code.

## 4. Phân tích chi tiết từng file

## 4.1. File `app.py`

Đây là file giao diện `Streamlit`.

### Vai trò chính

- Cho người dùng chọn dữ liệu đầu vào.
- Tạo `context` mô tả schema của dữ liệu.
- Gửi request sinh code đến backend.
- Hiển thị code để người dùng chỉnh sửa.
- Gửi code đã duyệt để backend thực thi.
- Hiển thị kết quả trả về.
- Hỗ trợ thêm chế độ chat thường với AI.

### Các hàm chính

#### `_repo_root()`
Trả về thư mục gốc của project.

#### `_default_raw_dir()`
Trả về đường dẫn mặc định đến thư mục dữ liệu thô:
`data/main/raw`.

#### `_list_raw_tables(raw_dir)`
Quét thư mục dữ liệu và lấy danh sách các file `.csv`.

Kết quả trả về là danh sách:
- tên bảng
- đường dẫn file

Ví dụ:
```python
[("orders", Path(".../orders.csv")), ("payments", Path(".../payments.csv"))]
```

#### `_load_schema_preview(csv_path, n_preview=20, n_sample=5)`
Đọc trước một phần nhỏ của file CSV để lấy:
- danh sách cột
- kiểu dữ liệu
- vài dòng sample
- vài dòng preview

Mục đích:
- không cần đọc toàn bộ file
- đủ thông tin để gửi context cho AI

Hàm này dùng `@st.cache_data`, nghĩa là Streamlit sẽ cache kết quả để tránh đọc đi đọc lại nhiều lần.

#### `_build_context(raw_dir, selected_tables, default_table)`
Tạo object `context` gửi sang backend/LLM.

Context có dạng:
```python
{
  "raw_dir": "...",
  "default_table": "orders",
  "tables": {
    "orders": {
      "columns": [...],
      "dtypes": {...},
      "sample": [...],
      "preview": [...],
      "preview_rows": 20
    }
  }
}
```

Ý tưởng rất quan trọng:
- AI chỉ thấy schema/sample
- AI không đọc trực tiếp file trong bước sinh code
- file thật chỉ được nạp ở bước thực thi

#### `_infer_used_tables(code, default_table)`
Đoán xem đoạn code đang dùng bảng nào bằng cách dò các pattern như:
- `tables["orders"]`
- `tables.get("orders")`
- hoặc dùng `df`

Hàm này chỉ phục vụ hiển thị trên UI, không phải kiểm tra chính thức.

#### `_post_json(url, payload)`
Helper gọi API `POST` và trả về JSON.

#### `_render_execution_result(result)`
Hiển thị kết quả thực thi lên giao diện:
- `summary`
- `stdout`
- biểu đồ PNG đã encode base64
- bảng dữ liệu
- `meta`

#### `main()`
Là hàm chính dựng toàn bộ giao diện Streamlit.

### Hai mode trong giao diện

#### `Chat`
Cho phép trò chuyện với AI, có thể kèm context của dataset, nhưng không sinh/chạy code.

#### `HITL Analysis`
Luồng phân tích chính:

1. Chọn bảng CSV
2. Chọn `default_table`
3. Nhập yêu cầu
4. Bấm `Generate code`
5. Xem/sửa code AI sinh ra
6. Bấm `Approve & Execute`
7. Xem kết quả

### State được lưu trong `st.session_state`

Một số giá trị quan trọng:
- `thread_id`: ID của phiên graph
- `generated_code`: code AI sinh ra
- `approved_code`: code sau khi người dùng duyệt/sửa
- `explanation`: giải thích đi kèm code
- `exec_result`: kết quả thực thi
- `chat_messages`: lịch sử chat
- `last_context`: context dataset gần nhất

## 4.2. File `main.py`

Đây là lớp API nằm giữa giao diện và graph.

### Vai trò chính

- Khởi tạo `FastAPI`
- Cho phép frontend gọi backend qua HTTP
- Tạo và tiếp tục phiên chạy graph theo `thread_id`
- Trả kết quả đúng format cho giao diện

### Thành phần chính

#### Import `build_graph`, `fetch_logs`, `chat_answer`
Lấy các hàm lõi từ `graph.py`.

#### `app = FastAPI(...)`
Khởi tạo ứng dụng backend.

#### `CORSMiddleware`
Cho phép frontend như Streamlit gọi API từ cổng khác.

#### `artifacts = build_graph()`
Tạo graph ngay khi server khởi động.

`artifacts` chứa:
- `graph`
- `checkpointer`
- `db_path`

#### `_mk_config(thread_id)`
Tạo config cho `LangGraph` theo từng phiên làm việc.

Mục đích:
- mỗi request phân tích có một `thread_id`
- graph nhớ được trạng thái đang dừng ở đâu

### Các model Pydantic

#### `GenerateRequest`
Input cho bước sinh code:
- `user_request`
- `context`
- `thread_id` tùy chọn

#### `GenerateResponse`
Output của bước sinh code:
- `thread_id`
- `status`
- `generated_code`
- `explanation`

#### `ExecuteRequest`
Input cho bước thực thi:
- `thread_id`
- `approved_code`

#### `ExecuteResponse`
Output của bước thực thi:
- `thread_id`
- `status`
- `execution_result`
- `logs`

#### `ChatRequest` / `ChatResponse`
Model cho chế độ chat thường.

### Các API endpoint

#### `POST /api/ai/generate`
Chức năng:
- nhận yêu cầu người dùng
- chạy graph đến điểm dừng trước `execute_code`
- trả code sinh ra và lời giải thích

Đây là bước "AI đề xuất code nhưng chưa chạy".

#### `POST /api/ai/execute`
Chức năng:
- nhận `approved_code`
- lấy lại state của graph theo `thread_id`
- cập nhật code đã được người dùng duyệt
- resume graph để chạy tiếp
- trả kết quả thực thi

Đây là bước "người dùng cho phép chạy code".

#### `GET /api/logs`
Đọc lịch sử từ SQLite.

#### `POST /api/ai/chat`
Trả lời câu hỏi bằng AI mà không đi qua luồng sinh/chạy code.

#### `GET /health`
Kiểm tra backend có đang sống hay không.

## 4.3. File `graph.py`

Đây là file quan trọng nhất của hệ thống.

### Vai trò chính

- định nghĩa state của workflow
- gọi OpenAI để sinh code
- giữ checkpoint của graph
- thực thi code đã duyệt trong môi trường bị giới hạn
- lưu log vào SQLite

## 5. Các thành phần chính trong `graph.py`

### 5.1. State và cấu trúc dữ liệu

#### `HITLState`
Là `TypedDict` mô tả dữ liệu chảy trong graph:

- `user_request`: yêu cầu người dùng
- `context`: schema dữ liệu
- `generated_code`: code AI sinh ra
- `explanation`: mô tả code
- `approved_code`: code sau khi người dùng duyệt
- `execution_result`: kết quả sau khi chạy
- `logs`: log trong suốt workflow
- `thread_id`: ID của phiên

#### `GraphArtifacts`
`dataclass` gom 3 thứ:
- `graph`
- `checkpointer`
- `db_path`

### 5.2. Các hàm tiện ích

#### `_utc_now_iso()`
Trả timestamp UTC theo chuẩn ISO.

#### `_json_dumps(obj)`
Chuyển object sang JSON string, hỗ trợ dữ liệu Unicode và object đặc biệt.

#### `_safe_json_loads(text)`
Cố gắng parse JSON từ output của model, kể cả khi model bọc trong markdown code fence.

#### `get_llm()`
Khởi tạo `ChatOpenAI` dựa trên:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

Nếu thiếu API key thì báo lỗi ngay.

#### `chat_answer(user_message, context=None)`
Phục vụ `Chat mode`.

Hàm này:
- tạo system prompt riêng
- cấm việc thực thi code
- cho phép AI trả lời dựa trên context dữ liệu nếu có

### 5.3. Logging nội bộ

#### `_add_log(state, msg)`
Thêm một dòng log có timestamp vào `state["logs"]`.

#### `init_db(db_path)`
Khởi tạo bảng `hitl_logs` trong SQLite nếu chưa có.

#### `insert_log(db_path, state)`
Ghi toàn bộ state quan trọng vào database.

#### `fetch_logs(db_path, limit=200)`
Đọc log từ database để trả về API.

## 6. Các node trong LangGraph

### `generate_code_node(state)`
Node này dùng LLM để sinh code phân tích dữ liệu.

#### Điểm đáng chú ý

- AI chỉ được dùng `pandas` và `matplotlib`
- AI không được đọc file
- AI không được gọi mạng
- AI không được import thêm thư viện
- AI phải kiểm tra cột trước khi dùng
- AI phải tạo biến `result` ở cuối

#### `result` được yêu cầu có cấu trúc
```python
result = {
  "summary": "...",
  "tables": [...],
  "figures": [...],
  "used_tables": [...]
}
```

#### Vì sao node này quan trọng

Nó đảm bảo AI chỉ "đề xuất cách phân tích", chưa được quyền chạy gì cả.

### `human_approval_node(state)`
Node giả để biểu diễn bước chờ con người duyệt.

Trên thực tế graph được cấu hình `interrupt_before=["execute_code"]`, nên workflow sẽ dừng trước khi vào bước chạy code.

### `execute_code_node(state)`
Node này:

1. Lấy `approved_code`
2. Nạp dữ liệu thật từ `context`
3. Thực thi code cục bộ
4. Thu kết quả
5. Ghi vào `execution_result`

Nếu code rỗng hoặc context sai thì trả lỗi phù hợp.

### `log_node_factory(db_path)`
Sinh ra một node dùng để lưu log vào SQLite.

Thiết kế theo factory để có thể gắn `db_path` động vào node.

### `build_graph(db_path=None)`
Là hàm lắp ráp toàn bộ workflow:

1. `START -> generate_code`
2. `generate_code -> human_approval`
3. `human_approval -> execute_code`
4. `execute_code -> log`
5. `log -> END`

Sau đó compile graph với:
- `MemorySaver()` để lưu checkpoint
- `interrupt_before=["execute_code"]` để ép buộc Human-in-the-loop

## 7. Cách thực thi code an toàn trong `graph.py`

Phần an toàn nằm chủ yếu trong `_safe_exec_analysis(...)`.

### Input của hàm

- `code`: code người dùng đã duyệt
- `df`: bảng mặc định
- `tables`: toàn bộ bảng đã nạp
- `default_table`
- `context`

### Các bước bảo vệ chính

#### 1. `_validate_code(user_code)`
Parse AST để chặn:
- `import`
- `open`
- `exec`
- `eval`
- `compile`
- `__import__`
- `input`
- các module nguy hiểm như `os`, `sys`, `subprocess`, `socket`
- truy cập attribute bắt đầu bằng `__`

#### 2. Giới hạn builtins
Chỉ cho phép một tập builtins nhỏ như:
- `print`
- `len`
- `range`
- `sum`
- `sorted`
- `list`
- `dict`
- `str`
- `int`
- `float`

#### 3. Giới hạn import nội bộ
Mặc dù user code bị cấm `import`, hệ thống vẫn allow-list một số thư viện nền để `pandas/matplotlib` hoạt động nội bộ:
- `pandas`
- `numpy`
- `matplotlib`
- `dateutil`
- `pytz`
- `math`
- `statistics`
- `re`

#### 4. Chỉ inject các biến cần thiết
Môi trường thực thi chỉ có:
- `pd`
- `plt`
- `df`
- `tables`
- `context`
- `require_columns`
- `pick_first_column`

#### 5. Thu kết quả có kiểm soát
Sau khi chạy `exec(...)`, hệ thống sẽ:
- bắt `stdout`
- chụp các figure mới tạo
- lấy biến `result`
- convert DataFrame sang JSON-friendly format

### Giới hạn hiện tại

Đây là môi trường "giới hạn rủi ro", chưa phải sandbox tuyệt đối của hệ điều hành.
Nghĩa là nó an toàn hơn `exec` bình thường, nhưng không phải bảo mật tuyệt đối 100%.

## 8. Cách nạp dữ liệu từ context

Phần này nằm trong `_load_tables_from_context(context)`.

Hệ thống hỗ trợ 2 kiểu context:

### Kiểu cũ: một file CSV
```python
{
  "csv_path": "/path/to/file.csv"
}
```

### Kiểu mới: nhiều bảng
```python
{
  "raw_dir": "/path/to/data/main/raw",
  "tables": {
    "orders": {...},
    "payments": {...}
  },
  "default_table": "orders"
}
```

Khi chạy thật:
- hệ thống đọc `${raw_dir}/{table_name}.csv`
- kiểm tra đường dẫn không bị path traversal
- tự chọn `default_table` nếu thiếu hoặc không hợp lệ

## 9. Cấu trúc kết quả thực thi

`execution_result` thường có dạng:

```python
{
  "stdout": "...",
  "summary": "...",
  "tables": [...],
  "images_base64_png": [...],
  "meta": {
    "python": "...",
    "executed_at": "...",
    "used_tables": [...],
    "default_table": "...",
    "available_tables": [...],
    "elapsed_sec": 0.1234
  }
}
```

Ý nghĩa:
- `stdout`: nội dung in ra từ `print`
- `summary`: tóm tắt kết quả
- `tables`: các bảng dữ liệu nhỏ để UI hiển thị
- `images_base64_png`: danh sách biểu đồ
- `meta`: metadata phục vụ debug/log

## 10. Vai trò của `prompt.md` và `readme.md`

### `prompt.md`
Không phải code chạy trực tiếp, nhưng rất quan trọng vì nó mô tả bài toán và ràng buộc kiến trúc ban đầu, ví dụ:
- Human-in-the-loop
- AI không tự chạy code
- FastAPI + LangGraph
- Streamlit để test

Có thể xem đây là "bản đặc tả nghiệp vụ" ban đầu.

### `readme.md`
Chứa lệnh chạy nhanh:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
streamlit run app/app.py
```

## 11. Tóm tắt nhanh từng file

### `app.py`
Frontend test và điều khiển luồng duyệt code.

### `main.py`
API backend nhận request và điều phối graph.

### `graph.py`
Logic cốt lõi: sinh code, dừng chờ duyệt, chạy code, lưu log.

### `logs.db`
Lưu lịch sử phân tích.

### `prompt.md`
Tài liệu yêu cầu hệ thống.

### `readme.md`
Tài liệu chạy ứng dụng.

## 12. Nếu muốn đọc code theo thứ tự dễ hiểu nhất

Nên đọc theo thứ tự này:

1. `app/readme.md`
2. `app/main.py`
3. `app/graph.py`
4. `app/app.py`
5. `app/prompt.md`

Lý do:
- `main.py` cho thấy API nào tồn tại
- `graph.py` cho thấy backend thật sự làm gì
- `app.py` cho thấy người dùng tương tác với backend ra sao

## 13. Kết luận

Thư mục `app` được tổ chức khá rõ theo 3 lớp:

1. `app.py`: lớp giao diện
2. `main.py`: lớp API
3. `graph.py`: lớp xử lý nghiệp vụ và workflow

Điểm quan trọng nhất của hệ thống là:
- AI không được tự chạy code
- người dùng luôn có bước duyệt
- việc thực thi chỉ xảy ra sau phê duyệt
- toàn bộ lịch sử được lưu lại để kiểm tra

Nếu bạn cần, tài liệu này có thể được mở rộng thêm thành:
- sơ đồ sequence diagram
- giải thích từng endpoint bằng ví dụ request/response
- giải thích từng hàm theo line-by-line
