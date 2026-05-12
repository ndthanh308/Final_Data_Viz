from __future__ import annotations

import ast
import base64
import io
import json
import os
import traceback
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")


class MultiAgentState(TypedDict, total=False):
    session_id: str
    chat_history: List[Dict[str, Any]]
    csv_schemas: Any
    user_request: str
    generated_code: str
    approved_code: str
    execution_result: Dict[str, Any]
    execution_error: str
    insights: str
    status: str


@dataclass
class GraphArtifacts:
    graph: Any
    checkpointer: Any


def _gio_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _them_lich_su(
    lich_su: Optional[List[Dict[str, Any]]],
    role: str,
    noi_dung: str,
    agent: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ds = list(lich_su or [])
    ds.append(
        {
            "time": _gio_utc_iso(),
            "role": role,
            "agent": agent or "",
            "content": noi_dung,
        }
    )
    return ds


def _llm() -> ChatOpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("Thiếu OPENAI_API_KEY. Vui lòng cấu hình biến môi trường trước khi chạy.")
    return ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.2)


def _bo_code_fence(text: str) -> str:
    noi_dung = (text or "").strip()
    if not noi_dung.startswith("```"):
        return noi_dung
    lines = noi_dung.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_json_an_toan(text: str) -> Dict[str, Any]:
    noi_dung = _bo_code_fence(text)
    try:
        return json.loads(noi_dung)
    except Exception:
        return {}


def supervisor_node(state: MultiAgentState) -> MultiAgentState:
    """Supervisor cập nhật trạng thái đầu vào trước khi định tuyến."""
    cap_nhat: MultiAgentState = {}
    if not state.get("status"):
        cap_nhat["status"] = "received_request"
    if state.get("user_request"):
        lich_su = state.get("chat_history", [])
        cuoi = lich_su[-1] if lich_su else {}
        if not (cuoi.get("role") == "user" and cuoi.get("content") == state.get("user_request", "")):
            cap_nhat["chat_history"] = _them_lich_su(
                lich_su,
                role="user",
                noi_dung=state.get("user_request", ""),
                agent="human",
            )
    return cap_nhat


def supervisor_router(state: MultiAgentState) -> Literal["code_generator", "tool_executor", "analyst", "end"]:
    trang_thai = (state.get("status") or "").strip()

    if trang_thai in {"received_request", "new_request"} and state.get("user_request"):
        return "code_generator"
    if trang_thai == "pending_approval":
        return "tool_executor"
    if trang_thai == "execution_succeeded":
        return "analyst"
    if trang_thai in {"execution_failed", "completed"}:
        return "end"
    return "end"


def code_generator_node(state: MultiAgentState) -> MultiAgentState:
    """Agent sinh code: chỉ tạo code, không thực thi."""
    user_request = (state.get("user_request") or "").strip()
    csv_schemas = state.get("csv_schemas", {})

    if not user_request:
        return {
            "status": "execution_failed",
            "execution_error": "Không có yêu cầu người dùng để sinh code.",
            "chat_history": _them_lich_su(
                state.get("chat_history"),
                role="assistant",
                agent="code_generator",
                noi_dung="Thiếu yêu cầu phân tích. Vui lòng nhập `user_request` rõ ràng hơn.",
            ),
        }

    he_thong = SystemMessage(
        content=(
            "Bạn là Code Generator Agent cho bài toán phân tích dữ liệu.\n"
            "Nhiệm vụ: sinh code Python dùng pandas/matplotlib thật chuẩn theo yêu cầu.\n"
            "Ràng buộc bắt buộc:\n"
            "- CHỈ sinh code, tuyệt đối không thực thi code.\n"
            "- Trả về đúng JSON có khóa: generated_code, note.\n"
            "- generated_code phải là code chạy được ngay.\n"
            "- Mọi giải thích nằm trong comment tiếng Việt trong code.\n"
            "- Không dùng import, không đọc mạng, không gọi shell.\n"
            "- Dữ liệu đầu vào khả dụng trong runtime:\n"
            "  * csv_tables: dict[str, pandas.DataFrame]\n"
            "  * df: pandas.DataFrame (bảng mặc định)\n"
            "- Code bắt buộc tạo biến result dạng dict có khóa:\n"
            "  * summary: str\n"
            "  * tables: list\n"
            "  * figures: list (để trống nếu không dùng)\n"
            "- Nếu thiếu cột quan trọng, raise ValueError với thông điệp tiếng Việt rõ ràng."
        )
    )
    nguoi_dung = HumanMessage(
        content=(
            "Sinh code phân tích dữ liệu dựa trên yêu cầu và ngữ cảnh schema sau.\n\n"
            f"YÊU CẦU:\n{user_request}\n\n"
            f"CSV_SCHEMAS_CONTEXT:\n{json.dumps(csv_schemas, ensure_ascii=False, default=str)}"
        )
    )

    llm = _llm()
    phan_hoi = llm.invoke([he_thong, nguoi_dung])
    noi_dung = phan_hoi.content if isinstance(phan_hoi.content, str) else str(phan_hoi.content)
    parsed = _parse_json_an_toan(noi_dung)

    generated_code = str(parsed.get("generated_code") or "").strip()
    note = str(parsed.get("note") or "").strip()
    if not generated_code:
        generated_code = _bo_code_fence(noi_dung)
        note = note or "Mô hình không trả JSON chuẩn, đã dùng nội dung thô."

    lich_su = _them_lich_su(
        state.get("chat_history"),
        role="assistant",
        agent="code_generator",
        noi_dung="Đã sinh code. Vui lòng kiểm duyệt rồi gửi `approved_code` để chạy.",
    )

    return {
        "generated_code": generated_code,
        "status": "pending_approval",
        "execution_error": "",
        "insights": "",
        "chat_history": lich_su,
        "execution_result": {},
        "approved_code": state.get("approved_code", ""),
        "user_request": user_request,
        "csv_schemas": csv_schemas,
        "session_id": state.get("session_id", ""),
        "note": note,
    }


def _ma_hoa_figure(fig: plt.Figure) -> str:
    bo_nho = io.BytesIO()
    fig.savefig(bo_nho, format="png", bbox_inches="tight", dpi=160)
    bo_nho.seek(0)
    return base64.b64encode(bo_nho.read()).decode("utf-8")


def _xac_thuc_code(code: str) -> None:
    """Kiểm tra AST để chặn các thao tác nguy hiểm rõ ràng."""
    cay = ast.parse(code)
    ten_cam = {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "input",
        "globals",
        "locals",
        "vars",
        "help",
        "breakpoint",
    }
    module_cam = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pathlib",
        "importlib",
        "builtins",
        "shutil",
    }

    for node in ast.walk(cay):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Không cho phép dùng import trong approved_code.")
        if isinstance(node, ast.Name) and node.id in ten_cam:
            raise ValueError(f"Không cho phép dùng `{node.id}` trong approved_code.")
        if isinstance(node, ast.Name) and node.id in module_cam:
            raise ValueError(f"Không cho phép truy cập module `{node.id}`.")
        if isinstance(node, ast.Attribute) and str(node.attr).startswith("__"):
            raise ValueError("Không cho phép truy cập dunder attribute.")


def _chuan_hoa_bang(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, pd.DataFrame):
        return {
            "type": "dataframe",
            "columns": [str(c) for c in obj.columns],
            "data": obj.head(200).to_dict(orient="records"),
        }
    if isinstance(obj, pd.Series):
        return {
            "type": "series",
            "name": str(obj.name),
            "data": obj.head(200).to_dict(),
        }
    if isinstance(obj, dict):
        return {"type": "dict", "data": obj}
    if isinstance(obj, list):
        return {"type": "list", "data": obj}
    return {"type": "text", "data": str(obj)}


def _thuc_thi_an_toan(code: str, csv_schemas: Any) -> Dict[str, Any]:
    """Thực thi code đã duyệt trong môi trường giới hạn."""
    _xac_thuc_code(code)

    tables_tho = csv_schemas if isinstance(csv_schemas, dict) else {}
    bang_df: Dict[str, pd.DataFrame] = {}
    for ten_bang, gia_tri in tables_tho.items():
        if isinstance(gia_tri, pd.DataFrame):
            bang_df[str(ten_bang)] = gia_tri.copy()
            continue
        if isinstance(gia_tri, dict):
            if isinstance(gia_tri.get("dataframe"), list):
                bang_df[str(ten_bang)] = pd.DataFrame(gia_tri["dataframe"])
                continue
            if isinstance(gia_tri.get("rows"), list):
                bang_df[str(ten_bang)] = pd.DataFrame(gia_tri["rows"])
                continue
            if isinstance(gia_tri.get("sample"), list):
                bang_df[str(ten_bang)] = pd.DataFrame(gia_tri["sample"])
                continue
        if isinstance(gia_tri, list):
            bang_df[str(ten_bang)] = pd.DataFrame(gia_tri)

    df_mac_dinh = next(iter(bang_df.values()), pd.DataFrame())

    allowed_builtins = {
        "print": print,
        "Exception": Exception,
        "ValueError": ValueError,
        "RuntimeError": RuntimeError,
        "len": len,
        "range": range,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "enumerate": enumerate,
        "isinstance": isinstance,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "str": str,
        "int": int,
        "float": float,
        "abs": abs,
        "round": round,
        "zip": zip,
        "any": any,
        "all": all,
    }

    globals_exec: Dict[str, Any] = {
        "__builtins__": allowed_builtins,
        "pd": pd,
        "plt": plt,
        "csv_tables": bang_df,
        "df": df_mac_dinh,
    }
    locals_exec: Dict[str, Any] = {}

    stdout_buffer = io.StringIO()
    fig_truoc = set(plt.get_fignums())
    try:
        with redirect_stdout(stdout_buffer):
            exec(code, globals_exec, locals_exec)
    finally:
        fig_sau = [n for n in plt.get_fignums() if n not in fig_truoc]
        charts = []
        for so in fig_sau:
            fig = plt.figure(so)
            charts.append(_ma_hoa_figure(fig))
        plt.close("all")

    ket_qua = locals_exec.get("result", globals_exec.get("result"))
    if not isinstance(ket_qua, dict):
        ket_qua = {
            "summary": "Code không tạo biến `result` dạng dict, hệ thống dùng kết quả mặc định.",
            "tables": [],
            "figures": [],
        }

    bang_kq: List[Dict[str, Any]] = []
    for item in ket_qua.get("tables", []) if isinstance(ket_qua.get("tables"), list) else []:
        bang_kq.append(_chuan_hoa_bang(item))

    return {
        "summary": str(ket_qua.get("summary", "")),
        "stdout": stdout_buffer.getvalue(),
        "tables": bang_kq,
        "charts_base64": charts,
        "executed_at": _gio_utc_iso(),
    }


def tool_executor_node(state: MultiAgentState) -> MultiAgentState:
    """Agent thực thi code đã được phê duyệt bởi con người."""
    approved_code = (state.get("approved_code") or "").strip()
    if not approved_code:
        loi = (
            "Thiếu `approved_code`, chưa thể chạy.\n"
            "Vui lòng gửi lại mã đã duyệt ở endpoint `/api/ai/execute`."
        )
        return {
            "status": "execution_failed",
            "execution_error": loi,
            "chat_history": _them_lich_su(
                state.get("chat_history"),
                role="assistant",
                agent="tool_executor",
                noi_dung=loi,
            ),
        }

    try:
        ket_qua = _thuc_thi_an_toan(approved_code, state.get("csv_schemas"))
        return {
            "status": "execution_succeeded",
            "execution_result": ket_qua,
            "execution_error": "",
            "chat_history": _them_lich_su(
                state.get("chat_history"),
                role="assistant",
                agent="tool_executor",
                noi_dung="Thực thi code thành công. Đang chuyển cho Analyst Agent tổng hợp insight.",
            ),
        }
    except Exception:
        tb = traceback.format_exc()
        loi = (
            "Thực thi code thất bại.\n"
            "Vui lòng tinh chỉnh lại prompt hoặc chỉnh sửa code trước khi chạy lại.\n\n"
            f"Chi tiết lỗi:\n{tb}"
        )
        return {
            "status": "execution_failed",
            "execution_result": {},
            "execution_error": loi,
            "chat_history": _them_lich_su(
                state.get("chat_history"),
                role="assistant",
                agent="tool_executor",
                noi_dung="Code chạy lỗi. Bạn có thể mô tả lại yêu cầu chi tiết hơn để hệ thống sinh code tốt hơn.",
            ),
        }


def _rut_gon_ket_qua_cho_analyst(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """Rút gọn payload trước khi gửi cho LLM để tránh quá dài."""
    if not isinstance(execution_result, dict):
        return {}

    tables_rut_gon: List[Dict[str, Any]] = []
    for bang in execution_result.get("tables", []) if isinstance(execution_result.get("tables"), list) else []:
        if isinstance(bang, dict):
            data = bang.get("data")
            if isinstance(data, list):
                data = data[:20]
            tables_rut_gon.append(
                {
                    "type": bang.get("type"),
                    "columns": bang.get("columns"),
                    "data": data,
                }
            )

    return {
        "summary": execution_result.get("summary", ""),
        "stdout": execution_result.get("stdout", "")[:4000],
        "tables": tables_rut_gon,
        "chart_count": len(execution_result.get("charts_base64", []) or []),
    }


def analyst_node(state: MultiAgentState) -> MultiAgentState:
    """Agent phân tích kết quả đã chạy và sinh insight kinh doanh."""
    execution_result = state.get("execution_result", {})
    if not isinstance(execution_result, dict) or not execution_result:
        thong_diep = "Không có dữ liệu đầu ra để phân tích insight."
        return {
            "status": "completed",
            "insights": thong_diep,
            "chat_history": _them_lich_su(
                state.get("chat_history"),
                role="assistant",
                agent="analyst",
                noi_dung=thong_diep,
            ),
        }

    tom_tat = _rut_gon_ket_qua_cho_analyst(execution_result)

    try:
        llm = _llm()
        he_thong = SystemMessage(
            content=(
                "Bạn là Analyst Agent chuyên phân tích kết quả data analytics cho business.\n"
                "Hãy tạo insight ngắn gọn, có hành động đề xuất, viết tiếng Việt.\n"
                "Ưu tiên nêu: xu hướng chính, bất thường, và khuyến nghị tiếp theo."
            )
        )
        nguoi_dung = HumanMessage(
            content=(
                f"YÊU CẦU GỐC:\n{state.get('user_request', '')}\n\n"
                f"KẾT QUẢ THỰC THI:\n{json.dumps(tom_tat, ensure_ascii=False, default=str)}"
            )
        )
        phan_hoi = llm.invoke([he_thong, nguoi_dung])
        insights = phan_hoi.content if isinstance(phan_hoi.content, str) else str(phan_hoi.content)
        insights = insights.strip() or "Không sinh được insight từ kết quả hiện tại."
    except Exception:
        insights = (
            "Đã chạy xong code nhưng chưa thể gọi Analyst Agent để tổng hợp insight.\n"
            "Bạn có thể dựa trên summary/table/chart để đánh giá thủ công."
        )

    return {
        "status": "completed",
        "insights": insights,
        "chat_history": _them_lich_su(
            state.get("chat_history"),
            role="assistant",
            agent="analyst",
            noi_dung=insights,
        ),
    }


def build_graph() -> GraphArtifacts:
    builder = StateGraph(MultiAgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("code_generator", code_generator_node)
    builder.add_node("tool_executor", tool_executor_node)
    builder.add_node("analyst", analyst_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "code_generator": "code_generator",
            "tool_executor": "tool_executor",
            "analyst": "analyst",
            "end": END,
        },
    )
    builder.add_edge("code_generator", "supervisor")
    builder.add_edge("tool_executor", "supervisor")
    builder.add_edge("analyst", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer, interrupt_before=["tool_executor"])
    return GraphArtifacts(graph=graph, checkpointer=checkpointer)
