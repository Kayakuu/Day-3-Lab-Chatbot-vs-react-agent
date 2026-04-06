# Group Report: Lab 3 - Production-Grade Agentic System (Bus Booking Agent)

- **Team Name**: Nhóm 04
- **Team Members**:
- ***1***. Trần Nhật Vĩ
- ***2***. Trần Thanh Phong
- ***3***. Nguyễn Tiến Huy Hoàng
- ***4***. Hoàng Đinh Duy Anh
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

Mục tiêu của dự án là xây dựng một ReAct Agent có khả năng hỗ trợ người dùng tra cứu chuyến xe, kiểm tra chính sách nhà
xe, xem thời tiết tuyến đường và tra cứu thông tin ngoài hệ thống cho các chuyến xe khách giữa các tỉnh thành tại Việt
Nam thông qua ngôn ngữ tự nhiên.

- **Coverage**: Hệ thống có 5 tool, được test end-to-end qua 30 lượt gọi thực tế (23 lượt ở chế độ Agent + 7 lượt ở chế
  độ Bare LLM làm baseline). Toàn bộ log nằm trong `logs/agent.log`.
- **Key Outcome**: Agent retrieve được dữ liệu thật cho mọi câu hỏi in-domain (tra chuyến, chính sách nhà xe, thời tiết,
  gợi ý quán ăn). Khi bị hỏi cùng một câu (`Chính sách hoàn vé COM-101?`, `Thời tiết Hà Giang?`), Bare LLM hoặc bịa đáp
  án, hoặc trả lời chung chung không có giá trị thực - chứng minh rõ giá trị của tool-use so với chatbot thuần.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

Hệ thống sử dụng vòng lặp ReAct để giải quyết các yêu cầu đa bước. Ví dụ thật từ `logs/agent.log` (row 29, prompt: *"Mai
tôi đi Hà Nội - Hà Giang, thời tiết Hà Giang thế nào? Có chuyến nào sáng sớm không?"*):

#### 2.1.1. Thought

Người dùng nói "mai" $\rightarrow$ cần biết hôm nay là ngày nào để chuyển sang `YYYY-MM-DD`. Sau đó cần tra chuyến Hà
Nội $\rightarrow$ Hà Giang
vào ngày mai và xem thời tiết Hà Giang ngày mai.

#### 2.1.2. Action

1. `get_current_datetime()` để lấy ngày hôm nay theo giờ Việt Nam.
2. `search_bus_schedules(origin="Hà Nội", destination="Hà Giang", departure_date="2026-04-07")`.
3. `get_route_weather(location="Hà Giang", date="2026-04-07")`.

#### 2.1.3. Observation

Lần lượt: chuỗi `2026-04-06 ...`, danh sách JSON các chuyến phù hợp, và một câu mô tả thời tiết Hà Giang bằng tiếng
Việt.

#### 2.1.4. Final Answer

Agent tổng hợp danh sách chuyến sáng sớm + dự báo thời tiết, nhắc người dùng nếu có mưa thì lưu ý hành lý chống nước.

### 2.2 Tool Definitions (Inventory)

| Tool Name               | Input                                                                                   | Use Case                                                                                                                |
|:------------------------|:----------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------|
| `search_bus_schedules`  | `origin, destination, departure_date?, max_price?, vehicle_type?, min_available_seats?` | Tra cứu chuyến xe khả dụng giữa hai tỉnh thành, có thể lọc theo ngày, giá, loại xe và số ghế trống.                     |
| `get_bus_operator_info` | `company_id` (mã `COM-xxx`)                                                             | Tra cứu chính sách hoàn vé, hành lý và tiện ích của một nhà xe cụ thể.                                                  |
| `get_current_datetime`  | (không)                                                                                 | Lấy ngày giờ hiện tại theo timezone `Asia/Ho_Chi_Minh` để chuyển các từ "hôm nay", "mai", "tối nay" thành `YYYY-MM-DD`. |
| `get_route_weather`     | `location, date?`                                                                       | Lấy thời tiết hiện tại hoặc dự báo (tới 5 ngày, OpenWeather) cho một địa điểm trên tuyến.                               |
| `web_search`            | `query`                                                                                 | Tra cứu các thông tin ngoài hệ thống (quán ăn gần bến, tình trạng đèo, v.v.) qua Tavily Search API.                     |

Tất cả 5 tool nằm trong `src/tools/bus_tools.py`, được register vào ReAct agent ở `src/agent/react_agent.py:53` (
`TOOLS = [...]`).

### 2.3 LLM Providers Used

- **Primary**: OpenAI `gpt-4o` (mặc định, có thể đổi qua biến môi trường `DEFAULT_MODEL`).
- **Client**: `langchain-openai.ChatOpenAI` được khởi tạo trong `build_agent()` và `build_bare_llm()` ở
  `src/agent/react_agent.py:62-80`.
- Hệ thống hiện chỉ wire một provider duy nhất; chưa có fallback model. Toàn bộ telemetry trong §3 được đo trên
  `gpt-4o`.

---

## 3. Telemetry & Performance Dashboard

Số liệu lấy từ `logs/agent.log` - 23 lượt gọi ở chế độ **Agent (có tool)** và 7 lượt ở chế độ **Bare LLM (không tool)**,
tất cả dùng `gpt-4o`. Loguru ghi mỗi cycle thành một JSON line với `latency_s`, `input_tokens`, `output_tokens`,
`estimated_cost_usd`, `mode`.

| Metric                    |                   Agent (n=23) |        Bare LLM (n=7) | Tỉ lệ Agent/Bare |
|:--------------------------|-------------------------------:|----------------------:|-----------------:|
| Latency P50               |                     **4.31 s** |                1.86 s |             2.3× |
| Latency P99               |                     **9.99 s** |                3.28 s |             3.0× |
| Tokens trung bình / lượt  | **2,998** (in 2,838 / out 159) | 549 (in 463 / out 86) |             5.5× |
| Tổng chi phí              |                    **$0.1999** |               $0.0141 |                - |
| Chi phí trung bình / lượt |                    **$0.0087** |               $0.0020 |             4.3× |

**Đọc kết quả:**

- Agent đắt hơn ~4.3× và chậm hơn ~2.3× ở P50 vì mỗi cycle phải gọi tool, đưa observation trở lại context window và suy
  luận tiếp - tiêu tốn input token tăng vọt (avg 2,838 vs 463).
- Đổi lại Agent trả lời được những câu Bare LLM không thể (xem §5).

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study: Multi-leg journey không có dữ liệu

- **Input** (logs/agent.log row 17): *"Có, hãy tìm giúp tôi 2 chuyến đi đó, thông tin khác như nào cũng được"* - tiếp
  nối câu hỏi trước về việc đi Hà Nội $\rightarrow$ Hồ Chí Minh, sau đó Hồ Chí Minh $\rightarrow$ Vũng Tàu.
- **Observation từ log**: Đây là cycle chậm nhất trong toàn bộ log tagged - **9.95 giây**, 2,387 input tokens, 186
  output tokens. Output thực tế của Agent: *"Hiện tại, không tìm thấy chuyến xe nào khớp với tiêu chí từ Hà Nội đi Hồ
  Chí Minh và từ Hồ Chí Minh đi Vũng Tàu. Bạn có thể thử thay đổi giờ đi, loại xe hoặc mức giá ... Nếu cần, bạn cũng có
  thể xem xét các phương tiện khác như máy bay hoặc tàu hỏa cho chặng Hà Nội - Hồ Chí Minh, sau đó tiếp tục bằng xe
  khách hoặc tàu cánh ngầm từ Hồ Chí Minh đi Vũng Tàu."* Agent đã decompose đúng cả 2 leg, gọi `search_bus_schedules`
  cho từng leg, nhận về `_NO_MATCH_MSG` cho cả hai và đưa ra fallback gợi ý phương tiện thay thế.
- **Root Cause**: Đây không phải lỗi reasoning của Agent - Agent xử lý đúng theo yêu cầu của người dùng. Vấn đề thật sự
  nằm ở **dataset coverage**:
- ***1***. **`data/bus_schedules.json` không có chuyến cho 2 cặp OD này**, dù đây là tuyến phổ biến nhất Việt Nam
  (HN-HCM, HCM-VT). Mock data của lab chỉ tập trung vào một vài tuyến mẫu.
- ***2***. **Latency cao do phải gọi nhiều tool tuần tự** (`get_current_datetime` $\rightarrow$ 2 lần
  `search_bus_schedules`) - khi
  cả hai leg đều miss, Agent phải reason thêm để sinh fallback message thay vì dừng ngay.
- **Solution**:
- ***1***. **Bổ sung dataset**: Mở rộng `data/bus_schedules.json` để cover các tuyến phổ biến (HN-HCM, HCM-VT, HN-Hải
  Phòng, ...) thay vì chỉ giữ vài tuyến demo.
- ***2***. **Cải thiện thông báo `_NO_MATCH_MSG`**: Hiện thông báo trong `src/tools/bus_tools.py:31-34` chỉ nói "không
  có chuyến khớp". Có thể bổ sung context về những filter nào đã apply để Agent biết nới lỏng filter nào trước.
- ***3***. **Parallel tool calls**: Hai lần gọi `search_bus_schedules` cho 2 leg là độc lập - LangGraph hỗ trợ parallel
  tool execution sẽ giảm latency của câu multi-leg này xuống ~ một nửa.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Agent (có tool) vs Bare LLM (không tool) trên cùng câu hỏi

Đây là thí nghiệm quan trọng nhất - chạy cùng một prompt qua hai cấu hình và so sánh kết quả thật từ log.

| Prompt                                                                                       | Agent (mode=agent)                                                                                                                                                                                         | Bare LLM (mode=bare)                                                                                                                   | Nhận xét                                                       |
|:---------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
| *"Chính sách hoàn vé của nhà xe COM-101 là gì?"*                                             | row 27: 2.79 s, 181 out tokens. Gọi `get_bus_operator_info("COM-101")` $\rightarrow$ trả về chính sách thật từ `data/operators.json`: *"Hủy trước 24h: hoàn 90%; 12–24h: hoàn 50%; dưới 12h: không hoàn"*. | row 36: 1.15 s, 51 out tokens. Không có tool $\rightarrow$ trả lời chung chung *"chính sách phụ thuộc vào nhà xe"*, không kèm số liệu. | Agent có dữ liệu thật, Bare LLM không thể answer correctly.    |
| *"Mai tôi đi Hà Nội - Hà Giang, thời tiết Hà Giang thế nào?"*                                | row 29: 9.99 s. Chuỗi 3 tool: `get_current_datetime` $\rightarrow$ `search_bus_schedules` $\rightarrow$ `get_route_weather`.                                                                               | row 37: 1.17 s, 48 out tokens. Trả lời generic *"thời tiết Hà Giang mùa này..."* không có dự báo cụ thể.                               | Agent chain được 3 tool trong cùng 1 cycle; Bare LLM phải bịa. |
| *"Cho tôi các chuyến xe từ Hà Nội đi Sa Pa ngày 2026-04-10, loại Sleeper, giá dưới 400000."* | row 24: 7.40 s. Gọi `search_bus_schedules` với đầy đủ filter, trả về danh sách thật.                                                                                                                       | row 38: 1.42 s, 84 out tokens. Trả lời chung chung tên một số nhà xe, không có giờ chạy / giá / số ghế.                                | Filter conjunctive chỉ hoạt động khi có tool.                  |

**Kết luận**: Bare LLM trả lời nhanh hơn ~3–8× và rẻ hơn ~4×, nhưng với câu cần dữ liệu cụ thể (chính sách nhà xe, giờ
chạy, thời tiết) thì kết quả không sử dụng được. Agent đánh đổi latency + cost để có ground truth.

### Experiment 2 (Bonus): Chatbot vs Agent - case-by-case

| Case                                                       | Bare LLM Result (logs/agent.log)        | Agent Result                                                          | Winner                       |
|:-----------------------------------------------------------|:----------------------------------------|:----------------------------------------------------------------------|:-----------------------------|
| *"Cho tôi các chuyến xe ... Sa Pa ... Sleeper ... < 400k"* | row 38: tên hãng generic, không có data | row 24: bảng chuyến xe thực tế từ JSON                                | **Agent**                    |
| *"Chính sách hoàn vé COM-101?"*                            | row 36: trả lời chung chung             | row 27: chính sách chính xác từ `operators.json`                      | **Agent**                    |
| *"Mai Hà Nội–Hà Giang, thời tiết?"*                        | row 37: generic                         | row 29: chuỗi 3 tool, có dự báo và chuyến xe sáng sớm                 | **Agent**                    |
| *"Bạn dạy tôi giải phương trình bậc hai được không?"*      | (không chạy bare cho câu này)           | row 32: 1.58 s, từ chối lịch sự, không gọi tool                       | Agent giữ scope tốt          |
| *"Tôi cần đi đâu đó cuối tuần này"*                        | (không chạy bare cho câu này)           | row 33: 1.77 s, hỏi lại điểm đi/điểm đến (fallback `_MISSING_OD_MSG`) | Clarification path hoạt động |

---

## 6. Production Readiness Review

- **Security - đã có**: Code tool kiểm tra API key trước khi gọi external service - `bus_tools.py:233-235` cho
  OPENWEATHER và `bus_tools.py:297-299` cho TAVILY - và quay về fallback message tiếng Việt khi key thiếu thay vì crash.
- **Guardrails - đã có**: Đã có hai cơ chế cơ bản hoạt động đúng trong log:
    - Câu out-of-domain (row 32, *"giải phương trình bậc hai"*) $\rightarrow$ agent từ chối lịch sự, không gọi tool.
    - Câu thiếu thông tin bắt buộc (row 33, *"đi đâu đó cuối tuần này"*) $\rightarrow$ agent gọi `search_bus_schedules`
      thiếu OD và
      nhận về `_MISSING_OD_MSG` fallback, sau đó hỏi lại người dùng.
- **Cải thiện đề xuất cho production**:
- ***1***. **Bổ sung dataset**: Mở rộng `data/bus_schedules.json` để cover các tuyến phổ biến (xem RCA §4).
- ***2***. **Giới hạn số vòng ReAct**: `build_agent()` ở `src/agent/react_agent.py:62-72` hiện không pass tham số giới
  hạn recursion - thêm để bảo vệ budget khi Agent rơi vào loop tool-call.
- ***3***. **Custom LangGraph node thay vì `create_react_agent` prebuilt**: Cho phép thêm logic state phức tạp như giữ
  giỏ vé tạm, xác nhận đặt chỗ trước khi commit.

---

> Link GIT: https://github.com/Kayakuu/Day-3-Lab-Chatbot-vs-react-agent
