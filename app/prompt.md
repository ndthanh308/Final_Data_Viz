Act as an expert Python backend developer specializing in LangChain, LangGraph, FastAPI, and OpenAI API.
I need to build an AI-powered data analysis API backend that strictly follows a "Human-in-the-loop" architecture. 

Here are the core system constraints and business rules that MUST be implemented:
1. [cite_start]**Roles**: The AI's job is to propose ideas, write Python (Pandas/Matplotlib) code based on user requests, and format results[cite: 7, 8, 9]. [cite_start]The AI MUST NOT execute code automatically[cite: 13, 14, 15].
2. [cite_start]**Code Generation & Explanation**: Whenever AI generates code, it must explicitly output the code and include natural language explanations directly as comments within the code (e.g., `# Đoạn code này sẽ...`)[cite: 22, 23].
3. [cite_start]**Approval Mechanism (Human-in-the-loop)**: Generated code must start in a "Pending" state[cite: 26]. [cite_start]The user (via frontend) has the right to view, edit, and approve the code[cite: 27, 28]. [cite_start]Code is ONLY executed after explicit human approval[cite: 29].
4. [cite_start]**Local Execution**: The approved code must be executed strictly on the local machine[cite: 13, 57].
5. [cite_start]**Separation of Concerns**: The system must be structured with decoupled APIs[cite: 36].

Please implement a LangGraph workflow exposed via FastAPI with the following requirements:

**A. LangGraph Definition:**
1. **State Definition**: Create a `TypedDict` State containing: `user_request`, `context` (data schema), `generated_code`, `explanation`, `approved_code`, `execution_result`, `logs`.
2. **Nodes**:
   - `generate_code_node`: Uses OpenAI API to generate Python code for data analysis and appends explanations as comments based on the user's request.
   - `human_approval_node`: A dummy node to represent the interrupt/breakpoint where the graph waits for user input.
   - `execute_code_node`: Safely executes the `approved_code` locally (using `exec` or a restricted environment) and captures stdout/charts/dataframes.
   - `log_node`: Saves the entire state (request, code, result, explanation) to a local SQLite database or file.
3. **Graph Compilation**: Build the StateGraph and compile it using a `MemorySaver` checkpointer to allow interruption before execution. Set the interrupt before `execute_code_node`.

**B. FastAPI Endpoints Required:**
1. [cite_start]`POST /api/ai/generate` (API AI): Receives the user request and dataset context from the frontend[cite: 50, 51, 52]. Invokes the LangGraph until it hits the human approval breakpoint. [cite_start]Returns the `generated_code` and `explanation`[cite: 54].
2. [cite_start]`POST /api/ai/execute` (API Thực thi): Receives the `approved_code` (which may have been edited by the user) and the thread `config`[cite: 55, 56]. [cite_start]Updates the graph state with the new code, resumes the graph execution locally [cite: 57][cite_start], and returns the collected execution results (charts, tables, logs)[cite: 58].
3. [cite_start]`GET /api/logs` (API Logs): Retrieves the history of all requests, source code, analysis results, and explanations from the storage[cite: 59, 60, 61].

Write complete, clean, and well-commented Python code for `main.py` (FastAPI setup) and `graph.py` (LangGraph setup). Ensure the local code execution logic captures outputs securely.


Make a simple UI using streamlit to test this pipeline