import json
import streamlit as st
from src.agent.agent import ReActAgent
from src.core.local_provider import LocalProvider

# Load mock data
try:
    with open("src/data/bus_schedules.json", "r", encoding="utf-8") as f:
        mock_data = json.load(f)
except Exception:
    mock_data = []

try:
    with open("src/data/operators.json", "r", encoding="utf-8") as f:
        operators_data = json.load(f)
except Exception:
    operators_data = {}

try:
    with open("src/data/mock_distances.json", "r", encoding="utf-8") as f:
        distances_data = json.load(f)
except Exception:
    distances_data = {}

def search_vehicles(query: str) -> str:
    """Tìm chuyến xe dựa trên điểm đến, điểm đi hoặc loại xe."""
    results = []
    # Chuẩn hóa query và các từ đồng nghĩa
    query_normalized = query.lower().replace("hồ chí minh", "tp.hcm").replace("hcm", "tp.hcm").replace("sài gòn", "tp.hcm")
    words = query_normalized.split()
    for v in mock_data:
        search_target = f"{v.get('origin', '')} {v.get('destination', '')} {v.get('vehicle_type', '')}".lower()
        if all(w in search_target for w in words):
            results.append(f"Mã: {v.get('id')} - {v.get('company_id')} ({v.get('origin')} -> {v.get('destination')}): {v.get('vehicle_type')}")
    if not results:
        return "Không tìm thấy chuyến xe phù hợp."
    return "\n".join(results[:10]) # Giới hạn 10 kết quả

def get_trip_details(trip_id: str) -> str:
    """Lấy chi tiết giá vé và thời gian của chuyến xe."""
    for v in mock_data:
        if trip_id.lower() in str(v.get('id', '')).lower():
            return f"Giá: {v.get('price')} VND. Đi lúc: {v.get('departure_time')}. Ghế trống: {v.get('available_seats')}."
    return "Không tìm thấy thông tin chuyến xe này."

def get_operator_info(company_id: str) -> str:
    """Lấy thông tin nhà xe từ mã nhà xe."""
    op = operators_data.get(company_id.strip().upper())
    if op:
        return f"Nhà xe {op.get('name')}. Chính sách hủy: {op.get('cancellation_policy')} Hành lý: {op.get('luggage_allowance')}"
    return "Không tìm thấy thông tin nhà xe."

def get_distance(loc1: str, loc2: str) -> str:
    """Lấy độ dài quãng đường giữa 2 vị trí."""
    for origin, routes in distances_data.items():
        if origin.lower() in loc1.lower() or loc1.lower() in origin.lower():
            for dest, dist in routes.items():
                if dest.lower() in loc2.lower() or loc2.lower() in dest.lower():
                    return f"Khoảng cách {origin} - {dest} là {dist} km."
        if origin.lower() in loc2.lower() or loc2.lower() in origin.lower():
            for dest, dist in routes.items():
                if dest.lower() in loc1.lower() or loc1.lower() in dest.lower():
                    return f"Khoảng cách {origin} - {dest} là {dist} km."
    return "Không có dữ liệu khoảng cách cho tuyến này."

tools_list = [
    {
        "name": "search_vehicles",
        "description": "Tìm kiếm tuyến xe, chuyến xe, loại xe dựa vào điểm đầu/cuối hoặc loại xe. Tham số: từ khóa tìm kiếm (vd: Sapa, Đà Lạt).",
        "func": search_vehicles
    },
    {
        "name": "get_trip_details",
        "description": "Lấy thông tin giá, giờ khởi hành và số ghế trống. Tham số: mã chuyến xe (vd: VN-001).",
        "func": get_trip_details
    },
    {
        "name": "get_operator_info",
        "description": "Lấy thông tin và chính sách nhà xe. Tham số: mã nhà xe (vd: COM-101).",
        "func": get_operator_info
    },
    {
        "name": "get_distance",
        "description": "Lấy khoảng cách giữa 2 điểm (km). Tham số: loc1 (vd: Hà Nội), loc2 (vd: Sa Pa).",
        "func": get_distance
    }
]

# UI Setup
from dotenv import load_dotenv
import os
from src.core.gemini_provider import GeminiProvider

load_dotenv()

st.set_page_config(page_title="Vehicle Booking Agent", layout="wide")

st.sidebar.title("⚙️ Cấu hình Model")
selected_model = st.sidebar.selectbox("Chọn Modal:", ["gemini-2.5-flash", "qwen2.5 (Local)"])

st.title("🚌 AI Vehicle Booking Agent")

@st.cache_resource(show_spinner=False)
def get_agent(model_choice):
    if "qwen2.5" in model_choice:
        llm_provider = LocalProvider(model_name="qwen2.5", base_url="http://localhost:11434")
    else:
        # Load API key from env
        api_key = os.environ.get("GEMINI_API_KEY", "")
        llm_provider = GeminiProvider(model_name="gemini-2.5-flash", api_key=api_key)
        
    return ReActAgent(llm=llm_provider, tools=tools_list, max_steps=7)

agent = get_agent(selected_model)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Bạn muốn tìm vé xe đi đâu?")

def stream_text(text, delay=0.02):
    import time
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Đang suy luận (ReAct loop)..."):
            from src.telemetry.metrics import tracker
            start_idx = len(tracker.session_metrics)
            
            final_answer = agent.run(user_input)
        
        # Áp dụng streaming cho câu trả lời cuối
        st.write_stream(stream_text(final_answer))
        
        new_metrics = tracker.session_metrics[start_idx:]
        if new_metrics:
            t_prompt = sum(m.get("prompt_tokens", 0) for m in new_metrics)
            t_comp = sum(m.get("completion_tokens", 0) for m in new_metrics)
            t_total = sum(m.get("total_tokens", 0) for m in new_metrics)
            t_latency = sum(m.get("latency_ms", 0) for m in new_metrics)
            t_cost = sum(m.get("cost_estimate", 0.0) for m in new_metrics)
            provider = new_metrics[0].get("provider", "Unknown")
            
            st.divider()
            st.caption("📊 **Metrics**")
            cols = st.columns(6)
            cols[0].metric("Provider", provider)
            cols[1].metric("Prompt", t_prompt)
            cols[2].metric("Completion", t_comp)
            cols[3].metric("Total", t_total)
            cols[4].metric("Latency (ms)", f"{t_latency}")
            cols[5].metric("Cost ($)", f"{t_cost:.5f}")
        
    st.session_state.messages.append({"role": "assistant", "content": final_answer})

