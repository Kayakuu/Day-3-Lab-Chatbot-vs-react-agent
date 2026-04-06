"""Streamlit chat UI for the Bus Booking ReAct agent."""

from __future__ import annotations

import json

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agent.react_agent import build_agent, build_bare_llm, run_agent, run_bare_llm

load_dotenv()

st.set_page_config(page_title="Bus Booking Agent", page_icon="🚌")
st.title("🚌 Bus Booking ReAct Agent")

mode = st.sidebar.radio(
    "Chế độ",
    ("Agent (có tool)", "Bare LLM (không tool)"),
    help="So sánh kết quả khi LLM được trang bị tool vs khi gọi API thuần.",
)
if st.sidebar.button("🗑 Xoá hội thoại"):
    st.session_state.messages = []
    st.rerun()

st.caption(
    "Tools: `search_bus_schedules`, `get_bus_operator_info`, `get_current_datetime`, "
    "`get_route_weather`"
    if mode.startswith("Agent")
    else "Không có tool — gọi LLM thuần"
)


@st.cache_resource
def get_agent():
    return build_agent()


@st.cache_resource
def get_bare_llm():
    return build_bare_llm()


if "messages" not in st.session_state:
    st.session_state.messages = []  # list[dict(role, content)]

agent = get_agent()
bare_llm = get_bare_llm()

# Replay history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Bạn muốn đi từ đâu đến đâu?")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    lc_history = []
    for m in st.session_state.messages:
        if m["role"] == "user":
            lc_history.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_history.append(AIMessage(content=m["content"]))

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            if mode.startswith("Agent"):
                result = run_agent(agent, lc_history, user_input)
            else:
                result = run_bare_llm(bare_llm, lc_history, user_input)

        for m in result["messages"]:
            if isinstance(m, ToolMessage):
                with st.expander(f"🔧 Tool: {m.name}"):
                    try:
                        st.json(json.loads(m.content))
                    except (ValueError, TypeError):
                        st.code(m.content)

        final_text = result["final_text"]
        st.markdown(final_text)

        metrics = result["metrics"]
        mode_tag = "agent" if mode.startswith("Agent") else "bare"
        st.caption(
            f"[{mode_tag}] ⏱ {metrics['latency_s']}s · "
            f"🧠 {metrics['model']} · "
            f"🔢 in {metrics['input_tokens']} / out {metrics['output_tokens']} · "
            f"💵 ${metrics['estimated_cost_usd']:.6f}"
        )

    st.session_state.messages.append({"role": "assistant", "content": final_text})
