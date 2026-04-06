# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Hoàng Đinh Duy Anh
- **Student ID**: 2A202600064
- **Date**: 2026-04-06
- **Role**: Tool Developer & UI/Telemetry Engineer

---

## I. Technical Contribution (15 Points)

Tôi phụ trách toàn bộ tầng tool, tầng UI và tầng telemetry của hệ thống - tức là mọi thứ bao quanh ReAct loop của
LangGraph.

### Modules implemented

| File                             | Vai trò                                                                                                                                |
|:---------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------|
| `src/tools/bus_tools.py`         | 5 tool LangChain (`@tool`) + Pydantic schema + helper load JSON + thông báo fallback tiếng Việt                                        |
| `src/agent/react_agent.py`       | Wire `create_react_agent` với 5 tool, viết `SYSTEM_PROMPT`, hàm `run_agent` / `run_bare_llm`, sum token usage qua nhiều `AIMessage`    |
| `src/telemetry/loguru_logger.py` | Loguru sink ghi JSON line, bảng giá `MODEL_PRICING`, hàm `estimate_cost_usd` (có prefix-match cho model ID có ngày), `log_agent_cycle` |
| `streamlit_app.py`               | UI chat đơn giản, sidebar chuyển đổi Agent vs Bare LLM, render `ToolMessage` trong `st.expander`, hiển thị metric/cost ở caption       |

### Code highlights

**1. Tool design pattern (xem `src/tools/bus_tools.py`)**

Mỗi tool tuân theo cùng một pattern: Pydantic `*Input` schema cho LLM thấy được tham số, decorator
`@tool("name", args_schema=...)`, và một bộ thông báo fallback tiếng Việt cố định để Agent có thể chuyển tiếp lỗi cho
người dùng một cách dễ chịu thay vì ném exception:

```python
_MISSING_OD_MSG = (
    "Lỗi: Thiếu điểm đi hoặc điểm đến. "
    "Hãy hỏi lại người dùng muốn đi từ đâu đến đâu."
)


@tool("search_bus_schedules", args_schema=SearchBusSchedulesInput)
def search_bus_schedules(origin, destination, departure_date=None, ...):
    if not origin or not destination:
        return _MISSING_OD_MSG
    ...
    return json.dumps(matches, ensure_ascii=False)
```

Pattern này được lặp lại cho cả 5 tool - mỗi tool luôn return `str` (hoặc JSON-encoded `str`) để LangGraph có thể nối
thẳng vào message history. Không tool nào ném exception ra ngoài; mọi failure mode (timeout, 404, key thiếu, query rỗng)
đều bị bắt và quy về một thông báo tiếng Việt cố định trong module-level constant.

**2. Tool 4 - `get_route_weather` với fallback graceful (`src/tools/bus_tools.py:217-274`)**

Đây là tool phức tạp nhất vì phải xử lý 2 endpoint khác nhau (current vs forecast), so sánh ngày với "hôm nay theo giờ
Việt Nam", và lọc dự báo 3-tiếng gần trưa nhất:

```python
today_str = datetime.now(VN_TZ).strftime("%Y-%m-%d")
use_forecast = bool(date) and date != today_str
url = OPENWEATHER_URL_FORECAST if use_forecast else OPENWEATHER_URL_CURRENT

try:
    resp = requests.get(url, params=params, timeout=EXTERNAL_TIMEOUT_S)
except (requests.Timeout, requests.ConnectionError, requests.RequestException):
    return _WEATHER_TIMEOUT_MSG
```

Khi `date` là tương lai $\rightarrow$ gọi forecast endpoint, lọc các slot 3 tiếng theo prefix `dt_txt`, chọn slot gần 12:00 trưa
nhất bằng `min(slots, key=_distance_to_noon)`. Khi key OpenWeather thiếu $\rightarrow$ cũng quay về `_WEATHER_TIMEOUT_MSG` để lab
vẫn chạy được end-to-end ngay cả khi user chưa cấu hình API key.

**3. Token aggregation qua nhiều `AIMessage` (`src/agent/react_agent.py:83-94`)**

Một cycle ReAct có thể chứa nhiều `AIMessage` (LLM gọi, tool trả về, LLM gọi tiếp...). Loguru cycle phải sum token qua
tất cả chúng, không chỉ message cuối:

```python
def _sum_token_usage(messages: List[BaseMessage]) -> Tuple[int, int]:
    in_tok, out_tok = 0, 0
    for m in messages:
        if not isinstance(m, AIMessage):
            continue
        usage = getattr(m, "usage_metadata", None)
        if usage:
            in_tok += int(usage.get("input_tokens", 0) or 0)
            out_tok += int(usage.get("output_tokens", 0) or 0)
    return in_tok, out_tok
```

Đây là điểm dễ sai nhất khi log Agent: nếu chỉ đọc `result["messages"][-1].usage_metadata` thì sẽ miss các vòng
tool-calling trước đó và underestimate cost. Telemetry thực tế trong `logs/agent.log` cho thấy mỗi cycle Agent có
trung bình 2,838 input tokens (vs 463 cho Bare LLM) - phần lớn nằm ở các `AIMessage` trung gian, không phải
message cuối.

**4. Loguru JSON-line sink (`src/telemetry/loguru_logger.py:28-44`)**

```python
logger.add(
    LOG_FILE, rotation="10 MB", retention="14 days",
    encoding="utf-8", enqueue=True,
    serialize=True,  # JSON lines: bound `extra` fields are included
    level="INFO",
)
```

`serialize=True` là chìa khóa: nó khiến mọi field `logger.bind(**payload)` được tự động dump vào field `record.extra`
của JSON line, để sau này tôi parse log bằng `json.loads(line)["record"]["extra"]` để aggregate metric.

**5. Streamlit UI tool message rendering (`streamlit_app.py:76-82`)**

```python
for m in result["messages"]:
    if isinstance(m, ToolMessage):
        with st.expander(f"🔧 Tool: {m.name}"):
            try:
                st.json(json.loads(m.content))
            except (ValueError, TypeError):
                st.code(m.content)
```

Vòng lặp này tự động render mọi tool call thành expander có thể bấm xem - không cần hardcode tên 5 tool. Khi bổ sung
tool mới sau này, UI tự pick up ngay.

### How it interacts with the ReAct loop

Toàn bộ ReAct loop được handle bởi `create_react_agent` của LangGraph; nhiệm vụ của tôi là:

1. **Đăng ký tool**:
   `TOOLS = [search_bus_schedules, get_bus_operator_info, get_current_datetime, get_route_weather, web_search]` được
   truyền vào `create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)`.
2. **Hướng dẫn agent qua prompt**: `SYSTEM_PROMPT` (`src/agent/react_agent.py:27-46`) liệt kê khi nào dùng tool nào -
   đặc biệt nhấn mạnh **bắt buộc gọi `get_current_datetime` trước** khi gặp từ "hôm nay/ngày mai", và không dùng
   `web_search` để tra chuyến.
3. **Đo lường loop**: `run_agent` time `agent.invoke()`, sum token, gọi `log_agent_cycle` với `extra={"mode": "agent"}`
   để mỗi cycle là một dòng JSON trong `logs/agent.log`.
4. **Cung cấp baseline**: `run_bare_llm` chạy `llm.invoke(...)` thuần, log với `extra={"mode": "bare"}` - cho phép so
   sánh trực tiếp Agent vs Chatbot trong Experiment 1 của group report.

---

## II. Debugging Case Study (10 Points)

### Problem: Loguru chỉ ghi `"agent_cycle"`, mất hết bound fields

**Triệu chứng**: Sau khi wire `log_agent_cycle` lần đầu, tôi mở `logs/agent.log` và chỉ thấy mỗi dòng có duy nhất chuỗi
`"agent_cycle"`. Tất cả `latency_s`, `input_tokens`, `output_tokens`, `model`, `estimated_cost_usd` mà tôi đã truyền qua
`logger.bind(**payload).info("agent_cycle")` đều biến mất.

**Log source** (snippet ban đầu):

```
2026-04-06 14:23:11.123 | INFO | src.telemetry.loguru_logger:log_agent_cycle:84 - agent_cycle
2026-04-06 14:23:18.456 | INFO | src.telemetry.loguru_logger:log_agent_cycle:84 - agent_cycle
```

$\rightarrow$ Hoàn toàn không có data để aggregate. Group report §3 không thể có số liệu.

**Diagnosis**: Loguru mặc định dùng formatter text - `bind(**payload)` chỉ inject field vào `record.extra` chứ không tự
stringify chúng vào message body. Để các field bound xuất hiện ở file output, có hai cách: (a) viết format string thủ
công gọi `{extra[key]}`, hoặc (b) bật `serialize=True` để loguru tự dump toàn bộ record (bao gồm `extra`) thành JSON
line.

Tôi đã chọn (b) vì:

1. Tôi muốn parse log lại bằng `json.loads()` (cho dashboard và group report telemetry);
2. Schema trong tương lai có thể đổi (thêm/xoá field), JSON-line tránh phải sửa format string mỗi lần;
3. Loguru `serialize=True` được thiết kế đúng cho use case structured logging.

**Solution**: Thêm `serialize=True` vào `logger.add(...)` trong `_configure()`:

```python
logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    enqueue=True,
    serialize=True,  # ← fix
    level="INFO",
)
```

**Verification**: Sau khi fix, mỗi dòng log trở thành 1 JSON object có `record.extra` chứa đầy đủ field. Đoạn
aggregation script (`json.loads(line)["record"]["extra"]`) chạy được trên 30 cycle, sinh ra bảng telemetry trong group
report §3 (P50 4.31 s, P99 9.99 s, total cost $0.1999 cho mode agent).

**Bài học**: Khi dùng structured logging library, luôn verify rằng output file thực sự chứa structured data, không chỉ
test bằng `print` hoặc `console`. Loguru console sink mặc định khác file sink - console thường tự pretty-print, file
sink thì im lặng nuốt field nếu thiếu format string.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning - vai trò của Thought block

Quan sát rõ nhất từ `logs/agent.log`: với prompt *"Mai tôi đi Hà Nội–Hà Giang, thời tiết Hà Giang thế nào? Có chuyến nào
sáng sớm không?"*

- **Bare LLM** (row 37, 1.17 s, 48 out tokens): trả lời generic kiểu *"Hà Giang vào tháng này thường mát mẻ..."* - không
  có giờ cụ thể, không có dự báo, không có chuyến xe.
- **Agent** (row 29, 9.99 s): Thought block phân rã thành 3 sub-task $\rightarrow$ gọi `get_current_datetime` để biết "mai" là ngày
  nào $\rightarrow$ gọi `search_bus_schedules` cho tuyến $\rightarrow$ gọi `get_route_weather` cho điểm đến $\rightarrow$ tổng hợp.

$\rightarrow$ Thought block không phải để LLM "suy nghĩ giỏi hơn", mà để **buộc LLM phải plan** trước khi action. Trong row 17
(multi-leg HN-HCM-VT, xem RCA group report §4), Thought block giúp Agent decompose đúng 2 leg và gọi
`search_bus_schedules` lần lượt - khi cả hai leg miss, Agent vẫn dùng observation để sinh fallback message gợi ý
phương tiện thay thế thay vì dừng ngay.

### 2. Reliability - khi Agent thực sự tệ hơn Chatbot

Có 2 trường hợp Agent ăn đậm latency mà giá trị thấp:

- **Câu hỏi đơn giản kiểu "có/không"** (vd: *"Có chuyến nào không?"* không kèm ngày). Agent vẫn cố tải
  `get_current_datetime` $\rightarrow$ `search_bus_schedules` $\rightarrow$ mất 4-5 s, trong khi Chatbot trả lời được trong 1.5 s với cùng độ
  chính xác.
- **Câu hỏi khái niệm** (vd: *"Bạn dạy tôi giải phương trình bậc hai được không?"* - row 32). Agent từ chối đúng (1.58
  s, không gọi tool) - tốt rồi, nhưng vẫn chậm hơn Bare LLM ~30% vì system prompt dài hơn 5× $\rightarrow$ input token cao hơn $\rightarrow$
  first-token latency cao hơn.

$\rightarrow$ Agent overhead là hằng số ~2-3 s/cycle dù không gọi tool. Trong production cần routing layer: câu nào "có khả năng cần
tool" mới đẩy vào Agent, còn lại đẩy thẳng vào Bare LLM.

### 3. Observation - observation thực sự ảnh hưởng next step

Ví dụ rõ nhất là row 17: *"Có, hãy tìm giúp tôi 2 chuyến đi đó, thông tin khác như nào cũng được"* (multi-leg
Hà Nội $\rightarrow$ HCM $\rightarrow$ Vũng Tàu).

Cả hai chặng đều trả về `_NO_MATCH_MSG` từ `search_bus_schedules`. Thay vì dừng ngay với "không tìm thấy", Agent đã
đọc observation, hiểu rằng cả hai leg đều thất bại, và **chủ động đề xuất phương án thay thế**: *"có thể xem xét các
phương tiện khác như máy bay hoặc tàu hỏa cho chặng Hà Nội - Hồ Chí Minh, sau đó tiếp tục bằng xe khách hoặc tàu cánh
ngầm từ Hồ Chí Minh đi Vũng Tàu"*. Bare LLM không có bước observation nào để dựa vào.

$\rightarrow$ Đây là điểm khác biệt căn bản. Agent có **error correction loop** miễn phí từ ReAct framework; Chatbot thì không. Các
tool message tiếng Việt tôi viết (`_NO_MATCH_MSG`, `_OPERATOR_NOT_FOUND_MSG`, ...) trong `src/tools/bus_tools.py` được
thiết kế để Agent có thể đọc + tự xử lý tiếp - không chỉ là thông báo lỗi cho user.

---

## IV. Future Improvements (5 Points)

Tất cả các đề xuất dưới đây đều bám vào file/hàm/đo lường đã có trong repo, không thêm dependency mới.

### Scalability

- **Cache JSON load**: `_load_bus_schedules()` và `_load_operators()` ở `src/tools/bus_tools.py:79-81` và `:139-141` đọc
  lại file đĩa mỗi lần tool được gọi. Vì hai file này read-only trong scope của lab, có thể đọc 1 lần ở module-level và
  reuse - giảm I/O cho mọi cycle.
- **Tightening `SYSTEM_PROMPT` cho multi-leg**: Telemetry §3 group report cho thấy P99 9.99 s rơi vào những câu chain
  nhiều tool. Bổ sung quy tắc trong `SYSTEM_PROMPT` (`src/agent/react_agent.py:27-46`) yêu cầu Agent liệt kê sub-task ở
  Thought block trước khi gọi tool, tránh trường hợp gọi `search_bus_schedules` thừa.

### Safety

- **Mở rộng pattern fallback hiện có**: Tôi đã viết 8 hằng số `_*_MSG` trong `bus_tools.py` (xem rows 32, 33 - cả hai
  đều fire đúng). Cùng pattern đó nên áp dụng cho các trường hợp chưa cover: vd `get_bus_operator_info` hiện chỉ check
  `company_id` rỗng, có thể thêm validate format `COM-xxx` để tránh Agent tự sáng tạo company_id.
- **Giới hạn vòng lặp ReAct**: `create_react_agent` trong LangGraph hỗ trợ tham số `recursion_limit`. Hiện `build_agent`
  ở `src/agent/react_agent.py:62-72` không truyền tham số này - nếu Agent rơi vào loop tool-call thì sẽ chạy vô hạn (cho
  đến khi LangGraph default cắt). Thêm giới hạn cứng để bảo vệ budget.

### Performance

- **Giảm input token mỗi cycle**: Đo từ `logs/agent.log`, Agent trung bình 2,838 input tokens/cycle so với 463 cho Bare
  LLM (~6×). Phần lớn là do `SYSTEM_PROMPT` được gửi lại mỗi lần. Rút gọn mô tả 5 tool trong prompt (giữ key info, bỏ
  ví dụ dài) sẽ trực tiếp giảm chi phí trên `gpt-4o`.
- **Cho phép đổi model qua UI**: `build_bare_llm` (`src/agent/react_agent.py:75`) đã có sẵn tham số `model_name:
  Optional[str] = None`. Streamlit sidebar có thể thêm dropdown để user chọn model rẻ hơn cho mode Bare LLM mà không
  cần sửa code agent.

---
