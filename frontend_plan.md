Act as an expert Python developer specializing in Streamlit and API integration.
I have a running FastAPI backend (Multi-Agent LangGraph) that handles data analysis with a strictly "Human-in-the-Loop" architecture. I need you to build a polished, modern Streamlit frontend to interact with these APIs.

**CRITICAL RULE:** All UI text, buttons, placeholders, and chat elements MUST be in Vietnamese.

**A. API Integration (Backend Context):**
The backend has 3 endpoints:
- `POST /api/ai/chat`: Sends `session_id`, user message, and CSV schemas. Returns AI thought process and a `generated_code` block that requires approval.
- `POST /api/ai/execute`: Sends `session_id` and `approved_code`. Returns chart data/images and business `insights`.
- `GET /api/sessions/{session_id}`: Retrieves chat history.

**B. UI / UX Requirements (`app.py`):**
1. **Sidebar - Session & Files:**
   - Allow users to "Tạo phiên mới" (Create new session) generating a unique session ID.
   - `st.file_uploader`: Support multi-file CSV uploads. Read these files, extract their `.head()` and column data types, and prepare them to be sent as string schema context to the backend.
2. **Main Chat Interface:**
   - Use `st.chat_message` to build a conversational UI. Display history.
   - User types a request -> Show a spinner -> Call `/api/ai/chat`.
3. **The Approval UI (Human-in-the-Loop):**
   - When the backend returns `generated_code`, render it inside an `st.text_area` or `st.code` block. 
   - Provide two explicit actions: an editable text box for the code, and an "Chấp thuận & Chạy code" (Approve & Execute) button.
   - When clicked, call `/api/ai/execute` with the code in the text box.
4. **Displaying Results & Insights:**
   - On successful execution, display any output dataframes. 
   - Render any generated charts seamlessly in the chat flow.
   - Display the Analyst Agent's `insights` using nicely formatted Markdown.
   - Handle backend execution errors gracefully by showing an error box and allowing the user to re-prompt.

Please write complete, clean, and interactive Streamlit code for `app.py`. Ensure state management (`st.session_state`) is handled robustly across app reruns.