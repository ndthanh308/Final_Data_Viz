Dưới đây là phiên bản **prompt hoàn chỉnh, rõ ràng, production-ready** để bạn đưa vào GPT-5/Gemini/Claude nhằm generate toàn bộ hệ thống AI Data Analysis theo kiến trúc Multi-Agent + Human-in-the-loop.

---

# PROMPT HOÀN CHỈNH

Bạn là một Senior Python Backend Engineer chuyên sâu về:

* Python
* FastAPI
* LangChain
* LangGraph
* OpenAI API
* Streamlit
* Multi-Agent Systems
* Human-in-the-loop AI Systems
* Secure Local Code Execution
* Data Analysis bằng Pandas/Matplotlib

Hãy thiết kế và viết hoàn chỉnh source code cho một hệ thống:

# “AI-Powered Data Analysis Platform”

theo kiến trúc:

* Multi-Agent Supervisor
* Human-in-the-loop
* FastAPI Backend
* LangGraph Workflow
* Streamlit Frontend

---

# YÊU CẦU QUAN TRỌNG NHẤT

## Toàn bộ hệ thống PHẢI dùng tiếng Việt

Bao gồm:

* UI
* API responses
* Agent responses
* System prompts
* Error messages
* Comments trong code AI generate
* Logging messages
* Insight phân tích dữ liệu
* Chat history

KHÔNG được xuất hiện tiếng Anh trong giao diện người dùng.

---

# KIẾN TRÚC TỔNG QUAN

Hệ thống gồm:

## 1. Backend

* FastAPI
* LangGraph
* OpenAI API
* Multi-Agent Supervisor Architecture
* Human-in-the-loop approval
* Local code execution
* Session persistence

## 2. Frontend

* Streamlit
* Chat UI
* Session management
* Multi-file CSV upload
* Editable generated code
* Human approval workflow
* Visualization rendering

---

# PHẦN 1 — MULTI-AGENT BACKEND

# A. KIẾN TRÚC AGENTS

Xây dựng hệ thống Multi-Agent gồm:

---

## 1. Supervisor Agent

Nhiệm vụ:

* Điều phối workflow
* Quyết định agent nào chạy tiếp theo
* Giám sát kết quả từ các agent
* Phân luồng:

  * Sinh code
  * Chờ approval
  * Execute
  * Retry khi lỗi
  * Phân tích insight

Supervisor phải sử dụng:

* LangGraph conditional edges
* next_node trong state

---

## 2. Code Generator Agent

Nhiệm vụ:

* Sinh Python code phân tích dữ liệu
* Dùng:

  * pandas
  * matplotlib
  * numpy
  * seaborn (nếu cần)
* Không bao giờ execute code
* Phải viết code sạch
* Có comments giải thích bằng tiếng Việt

Ví dụ:

```python
# Đoạn code này sẽ đọc dữ liệu doanh thu theo tháng
# Sau đó tính tổng doanh thu từng khu vực
```

Code phải hỗ trợ:

* nhiều CSV
* merge dữ liệu
* visualize
* thống kê
* xử lý missing values

---

## 3. Tool Executor Agent

Nhiệm vụ:

* Execute approved_code trên local machine
* Capture:

  * stdout
  * dataframe outputs
  * charts
  * traceback errors

Phải có:

## Sandbox execution

Dùng:

* exec()
* restricted globals
* io.StringIO
* contextlib.redirect_stdout

KHÔNG cho phép:

* os.system
* subprocess
* file deletion
* network requests

---

## Fallback Logic

Nếu execute lỗi:

* Catch traceback
* Lưu execution_error
* Trả về frontend hỏi user:

```text
Code thực thi gặp lỗi.
Bạn muốn:
1. Sinh lại code
2. Chỉnh sửa prompt
3. Chỉnh sửa code thủ công
```

---

## 4. Analyst Agent

Sau khi execute thành công:

* Phân tích outputs
* Sinh business insights bằng tiếng Việt
* Nhận xét:

  * trends
  * anomalies
  * correlations
  * recommendations

Ví dụ:

```text
Doanh thu quý 3 tăng mạnh 27% so với quý 2.
Khu vực miền Nam đóng góp hơn 58% tổng doanh thu.
```

---

# B. LANGGRAPH WORKFLOW

# State Definition

Tạo TypedDict:

```python
class AgentState(TypedDict):
    session_id: str
    chat_history: list
    multiple_csv_schemas: dict
    user_request: str

    generated_code: str
    approved_code: str

    execution_result: dict
    execution_error: str

    insights: str

    next_node: str
```

---

# Workflow Logic

Luồng xử lý:

```text
User Request
    ↓
Supervisor
    ↓
Code Generator
    ↓
[ HUMAN APPROVAL BREAKPOINT ]
    ↓
Tool Executor
    ├── Nếu lỗi → hỏi user → loop lại
    └── Nếu thành công
              ↓
         Analyst
              ↓
             END
```

---

# Human-in-the-loop

Code AI generate:

* KHÔNG được execute tự động
* Bắt buộc chờ user approve

User có thể:

* xem code
* edit code
* approve code

Chỉ execute sau approval.

---

# Checkpointer

Bắt buộc dùng:

```python
MemorySaver
```

hoặc:

```python
SqliteSaver
```

Key theo:

```python
thread_id = session_id
```

để:

* persist chat history
* resume workflow
* restore sessions

---

# C. FASTAPI BACKEND

Viết code hoàn chỉnh cho:

# `main.py`

Sử dụng:

* FastAPI
* Pydantic
* async endpoints

---

# API 1 — Chat API

## Endpoint

```python
POST /api/ai/chat
```

## Input

```json
{
  "session_id": "abc123",
  "user_request": "...",
  "uploaded_files": [...]
}
```

## Nhiệm vụ

* Parse nhiều CSV
* Tạo schema previews
* Trigger LangGraph
* Chạy đến breakpoint approval

## Response

```json
{
  "generated_code": "...",
  "message": "Vui lòng kiểm tra và phê duyệt code."
}
```

---

# API 2 — Execute API

## Endpoint

```python
POST /api/ai/execute
```

## Input

```json
{
  "session_id": "abc123",
  "approved_code": "..."
}
```

## Nhiệm vụ

* Resume graph từ breakpoint
* Execute local code
* Trigger analyst
* Return:

  * outputs
  * charts
  * insights
  * errors

---

# API 3 — Session API

## Endpoint

```python
GET /api/sessions/{session_id}
```

## Nhiệm vụ

Trả về:

* chat history
* generated code
* logs
* insights
* execution history

để frontend reload session.

---

# D. EXECUTION SECURITY

Phải implement:

## Restricted Execution Environment

Ví dụ:

```python
SAFE_BUILTINS = {
    "print": print,
    "len": len,
    "range": range,
}
```

Cho phép:

* pandas
* numpy
* matplotlib

Không cho phép:

* subprocess
* socket
* requests
* shutil
* os.system

---

# OUTPUT CAPTURE

Phải capture:

## stdout

Dùng:

```python
io.StringIO
redirect_stdout
```

---

## charts

Lưu:

```python
matplotlib figures → base64
```

---

## dataframe previews

Convert:

```python
df.head().to_dict()
```

---

# LOGGING

Lưu logs bằng:

* SQLite
  hoặc
* JSON file

Bao gồm:

* request
* generated code
* approved code
* execution results
* insights
* errors
* timestamps

---

# PHẦN 2 — STREAMLIT FRONTEND

Viết hoàn chỉnh:

# `app.py`

---

# A. GIAO DIỆN

UI hiện đại:

* responsive
* clean
* chat-style

Toàn bộ bằng tiếng Việt.

---

# B. SESSION MANAGEMENT

Sidebar gồm:

## Tạo phiên mới

Button:

```python
"Tạo phiên mới"
```

## Danh sách phiên cũ

Hiển thị:

* session history
* chọn session cũ

Dùng:

```python
st.session_state
```

và:

```python
session_id
```

để load lại hội thoại.

---

# C. MULTI-FILE CSV UPLOAD

Dùng:

```python
st.file_uploader(
    accept_multiple_files=True
)
```

Frontend phải:

* preview schema
* preview rows
* gửi metadata tới backend

---

# D. CHAT UI

Dùng:

```python
st.chat_message()
```

Cho:

* user
* AI
* errors
* analyst insights

---

# E. HUMAN APPROVAL UI

Generated code phải render trong:

```python
st.text_area()
```

Cho phép user:

* edit code
* approve code
* regenerate

Buttons:

```python
"Phê duyệt & Thực thi"
"Sinh lại code"
"Chỉnh sửa prompt"
```

---

# F. ERROR HANDLING UI

Nếu execute lỗi:

Hiển thị traceback đẹp.

Cho phép:

* retry
* regenerate
* edit prompt

---

# G. VISUALIZATION

Hiển thị:

* matplotlib charts
* plotly charts
* dataframe previews

Dùng:

```python
st.pyplot()
st.plotly_chart()
st.dataframe()
```
# H. Table review
Hiển thị:
- tables of input csv file
---

# FILES CẦN SINH

Hãy viết code hoàn chỉnh cho:

```text
project/
│
├── backend/
│   ├── main.py
│   ├── graph.py
│   ├── agents/
│   ├── services/
│   ├── database/
│   └── utils/
│
├── frontend/
│   └── app.py
│
├── requirements.txt
├── .env.example
└── README.md
```

---

# YÊU CẦU CODE

Code phải:

* production-ready
* modular
* clean architecture
* async nếu cần
* đầy đủ comments
* type hints
* dễ mở rộng
* có error handling
* có logging
* có docstrings

---

# THƯ VIỆN BẮT BUỘC

Sử dụng:

```python
langgraph
langchain
langchain-openai
fastapi
uvicorn
streamlit
pandas
matplotlib
plotly
sqlite3
python-dotenv
```

---

# OUTPUT MONG MUỐN

Hãy sinh:

1. `graph.py`
2. `main.py`
3. `app.py`
4. `requirements.txt`
5. `.env.example`
6. `README.md`

Code phải đầy đủ, chạy được ngay, không pseudo-code.

Nếu file quá dài:

* chia thành nhiều phần rõ ràng
* mỗi phần có tiêu đề
* không được bỏ sót import
* không được viết placeholder kiểu “TODO”
