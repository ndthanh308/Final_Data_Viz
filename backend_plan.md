Act as an expert Python backend developer specializing in LangChain, LangGraph, FastAPI, and OpenAI API.
I am building the backend for a "Human-in-the-loop" AI data analysis system. I need a Multi-Agent architecture managed by a Supervisor, exposed completely via REST APIs.
NO FRONTEND CODE (No Streamlit) needed for this task.

**CRITICAL RULE:** All system messages, natural language responses, and code comments MUST be in Vietnamese.

**A. Multi-Agent Roles & Responsibilities:**
1. **Supervisor Agent**: Routes the workflow based on the current state.
2. **Code Generator Agent**: Writes perfect Python (Pandas/Matplotlib) code based on user requests and provided CSV schemas. It appends explanations as comments (e.g., `# Đoạn code này sẽ...`). It DOES NOT execute code.
3. **Tool Executor Agent**: Safely executes the strictly *approved* code locally. Captures stdout, charts (as base64 or saved files), and dataframes. If execution fails, it catches the traceback and routes back to output an error message asking the user for prompt enhancement.
4. **Analyst Agent**: Reviews the correctly executed outputs (data/charts) and generates meaningful business insights.

**B. LangGraph State & Workflow:**
1. **State Definition (`TypedDict`)**: Include `session_id`, `chat_history`, `csv_schemas` (list/dict), `user_request`, `generated_code`, `approved_code`, `execution_result`, `execution_error`, `insights`, `status` (e.g., pending_approval, completed).
2. **Workflow Mechanism**: User Request -> Supervisor -> Code Generator -> **[HUMAN APPROVAL BREAKPOINT]**. (Graph pauses here).
3. **Resume Workflow**: Once approved code is submitted -> Tool Executor. If success -> Analyst -> End. If fail -> Update error -> End (wait for new user instructions).
4. **Memory**: Use `MemorySaver` keyed by `thread_id` (session_id) to persist graph states.

**C. FastAPI Endpoints Required (`main.py`):**
1. `POST /api/ai/chat`: Accepts `session_id`, `user_request`, and raw `csv_schemas_context`. Triggers the graph until it hits the Human Approval Breakpoint. Returns the `generated_code`.
2. `POST /api/ai/execute`: Accepts `session_id` and the `approved_code` (user edited/confirmed). Resumes the graph. Returns the final execution results (data/plots) and `insights`.
3. `GET /api/sessions/{session_id}`: Retrieves state and history of a specific session.

Please write complete, modular, and well-commented Python code for:
- `graph.py` (LangGraph Multi-Agent setup and local execution logic)
- `main.py` (FastAPI router setup, schemas, and endpoints)