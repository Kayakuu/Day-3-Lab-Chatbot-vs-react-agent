"""ReAct agent wired with the bus-booking tools.

Uses LangGraph's prebuilt `create_react_agent` so the tool-calling loop,
message history, and observation feedback are all handled for us. Only the
first tool (`search_bus_schedules`) is registered for now.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.telemetry.loguru_logger import log_agent_cycle
from src.tools.bus_tools import search_bus_schedules

SYSTEM_PROMPT = (
    "Bạn là trợ lý đặt vé xe khách tại Việt Nam. "
    "Khi người dùng muốn tra cứu chuyến xe, hãy gọi tool `search_bus_schedules` "
    "với điểm đi và điểm đến (bắt buộc), kèm các bộ lọc tùy chọn nếu người dùng "
    "có nhắc tới (ngày khởi hành YYYY-MM-DD, giá tối đa, loại xe, số ghế tối thiểu). "
    "Nếu thiếu điểm đi hoặc điểm đến, hãy hỏi lại người dùng. "
    "Sau khi nhận kết quả từ tool, tóm tắt ngắn gọn các chuyến phù hợp bằng tiếng Việt "
    "(mã chuyến, giờ khởi hành, giá, số ghế trống, loại xe). "
    "Nếu tool trả về thông báo lỗi/không có chuyến, hãy chuyển tiếp ý đó cho người dùng."
)

BARE_SYSTEM_PROMPT = (
    "Bạn là trợ lý đặt vé xe khách tại Việt Nam. "
    "Trả lời ngắn gọn câu hỏi của người dùng dựa trên kiến thức của bạn."
)

TOOLS = [search_bus_schedules]


def build_agent(model_name: Optional[str] = None, temperature: float = 0.0):
    """Create a ReAct agent bound to the bus-booking tools.

    The compiled graph is tagged with the model name on its config so the
    runner can read it back when logging.
    """
    model_name = model_name or os.getenv("DEFAULT_MODEL", "gpt-4o")
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    graph = create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)
    graph._model_name = model_name  # type: ignore[attr-defined]
    return graph


def build_bare_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatOpenAI:
    """Plain ChatOpenAI client with no tools — for the bare-LLM baseline."""
    model_name = model_name or os.getenv("DEFAULT_MODEL", "gpt-4o")
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    llm._model_name = model_name  # type: ignore[attr-defined]
    return llm


def _sum_token_usage(messages: List[BaseMessage]) -> Tuple[int, int]:
    """Sum input/output tokens across every AIMessage in an agent run."""
    in_tok = 0
    out_tok = 0
    for m in messages:
        if not isinstance(m, AIMessage):
            continue
        usage = getattr(m, "usage_metadata", None)
        if usage:
            in_tok += int(usage.get("input_tokens", 0) or 0)
            out_tok += int(usage.get("output_tokens", 0) or 0)
    return in_tok, out_tok


def run_agent(agent, history: List[BaseMessage], user_input: str) -> Dict[str, Any]:
    """Invoke the agent on a chat history, log one cycle, and return the result.

    `history` should already contain the new HumanMessage as its last entry.
    Returns a dict with keys: messages, final_text, metrics.
    """
    model_name = getattr(agent, "_model_name", "unknown")
    start = time.perf_counter()
    result = agent.invoke({"messages": history})
    latency = time.perf_counter() - start

    messages: List[BaseMessage] = result["messages"]
    final_text = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            final_text = m.content if isinstance(m.content, str) else str(m.content)
            break

    in_tok, out_tok = _sum_token_usage(messages)
    metrics = log_agent_cycle(
        user_input=user_input,
        agent_output=final_text,
        model=model_name,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_s=latency,
        extra={"mode": "agent"},
    )
    return {"messages": messages, "final_text": final_text, "metrics": metrics}


def run_bare_llm(llm: ChatOpenAI, history: List[BaseMessage], user_input: str) -> Dict[str, Any]:
    """Single LLM call with no tools, no agent loop. Logs the same metrics."""
    model_name = getattr(llm, "_model_name", "unknown")
    messages: List[BaseMessage] = [SystemMessage(content=BARE_SYSTEM_PROMPT), *history]

    start = time.perf_counter()
    response = llm.invoke(messages)
    latency = time.perf_counter() - start

    final_text = response.content if isinstance(response.content, str) else str(response.content)
    usage = getattr(response, "usage_metadata", None) or {}
    in_tok = int(usage.get("input_tokens", 0) or 0)
    out_tok = int(usage.get("output_tokens", 0) or 0)

    metrics = log_agent_cycle(
        user_input=user_input,
        agent_output=final_text,
        model=model_name,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_s=latency,
        extra={"mode": "bare"},
    )
    return {"messages": [response], "final_text": final_text, "metrics": metrics}
