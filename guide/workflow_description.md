Dưới đây là phần mô tả chi tiết và các sơ đồ Mermaid đã được cập nhật hoàn toàn để phản ánh kiến trúc Tool mới của bạn (
`search_bus_schedules`, `get_bus_operator_info`, `get_current_datetime`, `get_route_weather`, `web_search`). Việc gộp
các tool nhỏ thành các tool tra cứu mạnh mẽ hơn sẽ làm cho các luồng xử lý này mượt mà và ít token hơn.

### Master Router: Phân loại Intent & Điều hướng (The Brain of the Agent)

*This outlines the high-level decision-making process before any specific tool loop begins, ensuring efficiency and
strict boundary control.*

* **Bắt đầu:** User gửi một request bất kỳ vào hệ thống.
* **Thought:** Cần phân tích ý định (intent) của câu hỏi để quyết định xem có cần mở vòng lặp ReAct hay không, và nếu có
  thì dùng nhóm Tool nào.
* **Action (Routing):** Đánh giá request dựa trên 4 nhóm:
    1. Core Domain (Tìm lịch trình, lọc xe, lấy thời gian thực).
    2. Policy (Quy định nhà xe, hành lý, tiện ích).
    3. Trải nghiệm/Ngoại vi (Thời tiết, cảnh đẹp, quán ăn).
    4. Out-of-scope (Hoàn toàn không liên quan).
* **Observation:** (Bước định tuyến logic bên trong LangChain, không gọi API ngoài).
* **Kết thúc:** Đẩy request vào nhánh xử lý tương ứng.
* **Telemetry:** Ghi nhận `Intent_Category` vào LangSmith để theo dõi xu hướng hỏi của người dùng.

---

### Case 1: Tra cứu quy định chung (Static RAG / System Prompt)

*This proves the system doesn't waste tokens or latency looping through tools when the answer is already in its prompt
or general knowledge base.*

* **Bắt đầu:** "Hướng dẫn tôi các bước thanh toán vé xe trên hệ thống."
* **Thought:** Câu hỏi thuộc nhóm Hướng dẫn sử dụng chung/FAQ. Thông tin đã có sẵn trong System Prompt hoặc tài liệu
  RAG, không cần tra cứu dữ liệu nhà xe cụ thể hay lịch trình.
* **Action:** Quyết định không sinh ra định dạng JSON Tool Call.
* **Observation:** (Không kích hoạt Tool kỹ thuật nào).
* **Kết thúc:** Trực tiếp chuyển sang trạng thái Final Answer, trả lời ngay cho người dùng: "Để thanh toán, bạn vui lòng
  làm theo 3 bước sau...".
* **Telemetry:** Ghi nhận `Total_Loops = 1`, `Tool_Calls = 0`. Tối ưu chi phí và cho độ trễ (latency) cực thấp.

---

### Case 2: Giải đáp chính sách nhà xe cụ thể (Simple Data Retrieval)

*This shows a successful, single-iteration tool execution smoothly passing through Pydantic guardrails.*

* **Bắt đầu:** "Chính sách hành lý của nhà xe Phương Trang thế nào?"
* **Thought:** Cần lấy thông tin quy định chi tiết của một nhà xe cụ thể từ cơ sở dữ liệu.
* **Action:** Sinh JSON gọi tool `get_bus_operator_info(company_id="COM-101")`. Pydantic kiểm tra format hợp lệ.
* **Observation:** Tool đọc file `operators.json` và trả về JSON:
  `{"luggage_allowance": "Tối đa 20kg hành lý ký gửi..."}`.
* **Kết thúc:** LLM nhận dữ liệu, định dạng lại thành câu trả lời tự nhiên và đưa ra Final Answer.
* **Telemetry:** Ghi nhận HTTP 200 OK, 1 Successful Tool Call.

---

### Case 3: Đặt xe với tiêu chí phức tạp (Complex Multi-step & Error Recovery)

*This highlights the true power of an Agent: reasoning across multiple steps and utilizing "Self-Correction" when
Pydantic rejects a bad input.*

* **Bắt đầu:** "Tìm xe giường nằm Hà Nội - Sa Pa ngày mai, giá rẻ."
* **Thought 1 & Action 1:** Từ "ngày mai" yêu cầu ngữ cảnh thời gian thực -> Gọi `get_current_datetime()`. -> *
  *Observation 1:** "2024-04-10 14:30:00".
* **Thought 2 & Action 2 (Error):** Lọc chuyến xe ngày 11/04 -> LLM dịch từ "giá rẻ" thành chuỗi string và gọi tool sai
  kiểu dữ liệu: `search_bus_schedules(origin="Hà Nội", destination="Sa Pa", max_price="rẻ")`.
* **System Fallback:** Pydantic chặn lại vì `max_price` phải là kiểu số (Integer). Gửi ngược lỗi vào prompt làm
  Observation: *"Pydantic Error: max_price must be an integer"*.
* **Thought 3 & Action 3 (Retry):** LLM nhận ra lỗi -> Tự sửa lại, loại bỏ tham số `max_price` bị lỗi hoặc gán một mức
  giá trần hợp lý:
  `search_bus_schedules(origin="Hà Nội", destination="Sa Pa", departure_date="2024-04-11", vehicle_type="Sleeper")`. ->
  **Observation 3:** Trả về danh sách xe.
* **Kết thúc:** Trình bày danh sách chuyến xe phù hợp cho người dùng.
* **Telemetry:** Ghi nhận vòng lặp tự sửa lỗi (Self-correction loop), log lại 1 Pydantic Validation Error để tối ưu.

---

### Case 4: Lịch trình kết hợp Trải nghiệm (Hybrid: Internal + Weather/Web Search)

*This demonstrates the agent's awareness of its own database limits, seamlessly mixing internal tools with external APIs
for a complete travel advisory.*

* **Bắt đầu:** "Có chuyến xe nào từ Đà Nẵng đi Hội An hôm nay không? Tiện thể xem thời tiết ở Hội An và gợi ý vài quán
  ăn quanh bến xe Hội An nhé."
* **Thought 1 & Action 1:** Cần kiểm tra lịch trình -> Gọi `get_current_datetime()` sau đó gọi
  `search_bus_schedules(origin="Đà Nẵng", destination="Hội An")`. -> **Observation 1:** Trả về các chuyến đi Hội An
  trong ngày.
* **Thought 2 & Action 2:** Khách hỏi về thời tiết -> Gọi tool `get_route_weather(location="Hội An")`. -> **Observation
  2:** "Trời nắng đẹp, 28 độ C".
* **Thought 3 & Action 3:** Cần thông tin quán ăn, không có trong DB -> Gọi
  `web_search(query="Quán ăn ngon gần bến xe Hội An")`. -> **Observation 3:** Trả về tóm tắt từ Google/Tavily (Cơm gà Bà
  Buội, Cao Lầu Thanh...).
* **Kết thúc:** Kết hợp số liệu cứng (lịch xe) và thông tin trải nghiệm (thời tiết, món ăn) để đưa ra câu trả lời toàn
  diện.
* **Telemetry:** Ghi nhận sử dụng 3 Tools khác nhau (2 Internal, 1 External).

---

### Case 5: Thiếu thông tin (Edge Case - Pydantic Guardrails)

*This proves the agent won't blindly hallucinate inputs when missing crucial data.*

* **Bắt đầu:** "Tìm cho tôi một chuyến xe."
* **Thought:** Cần gọi `search_bus_schedules` để tìm xe.
* **Action (Schema Check):** LLM đối chiếu ý định với Pydantic schema của tool `search_bus_schedules`. Nhận thấy các
  biến `origin` và `destination` là các tham số Bắt buộc (Required).
* **Fallback Decision:** Vì người dùng chưa cung cấp điểm đi và điểm đến, LLM hiểu rằng việc cố đoán (hallucinate) địa
  điểm sẽ bị Pydantic chặn. Quyết định "Short-circuit" (ngắt sớm vòng lặp).
* **Observation:** Không kích hoạt tool kỹ thuật nào.
* **Kết thúc:** Trực tiếp chuyển sang Final Answer, yêu cầu người dùng cung cấp thông tin: "Bạn dự định đi từ đâu đến
  đâu để tôi kiểm tra lịch xe nhé?"
* **Telemetry:** Hoàn thành trong 1 loop. Tiết kiệm token/chi phí.

---

### Case 6: Câu hỏi ngoài luồng (Out-of-Scope Guardrails)

*This guarantees the agent protects business boundaries and budget by refusing to process or web-search irrelevant
topics.*

* **Bắt đầu:** "Hướng dẫn tôi giải phương trình Toán học" (Hoặc "Thị trường chứng khoán hôm nay thế nào?")
* **Thought:** Người dùng hỏi về chủ đề hoàn toàn không liên quan đến dịch vụ đặt xe hay du lịch.
* **Action (Policy Check):** Đối chiếu với bộ Guardrails trong System Prompt. Mệnh lệnh "Không hỗ trợ ngoài lề" được
  kích hoạt. Tuyệt đối không được dùng Tool `web_search` cho các truy vấn này.
* **Observation:** Không kích hoạt bất kỳ vòng lặp Tool nào.
* **Kết thúc:** Trả lời từ chối lịch sự theo mẫu: "Cảm ơn bạn, tôi là trợ lý AI chuyên hỗ trợ đặt vé xe. Tôi không thể
  giúp bạn giải đáp vấn đề này."
* **Telemetry:** Log `Out_Of_Scope_Rejected`.

---

Dưới đây là bộ **6 sơ đồ Mermaid hoàn chỉnh nhất** phản ánh kiến trúc Tool mới:

### 0. Master Router (Luồng phân loại điều hướng tổng quát)

```mermaid
graph TD
    Start([User Request]) --> Router{Phân loại Intent & Domain}
%% Nhánh 1: Core Domain
    Router -->|Tìm chuyến, ngày giờ, lịch trình| CoreDomain[Nhóm Internal Core]
    CoreDomain --> T_Search[search_bus_schedules]
    CoreDomain --> T_Time[get_current_datetime]
%% Nhánh 2: Policy
    Router -->|Quy định, hành lý, nhà xe| PolicyDomain[Nhóm DB/Policy]
    PolicyDomain --> T_Info[get_bus_operator_info]
%% Nhánh 3: Ngoại vi nhưng liên quan
    Router -->|Thời tiết, trải nghiệm, quán ăn| WebDomain[Nhóm External API]
    WebDomain --> T_Weather[get_route_weather]
    WebDomain --> T_Web[web_search]
%% Nhánh 4: Out of Scope
    Router -->|Hoàn toàn không liên quan di chuyển| OutOfScope[Từ chối phục vụ]
    OutOfScope --> End_OOS([Trả lời từ chối lịch sự])
    classDef core fill: #d4edda, stroke: #28a745, stroke-width: 2px;
    classDef policy fill: #cce5ff, stroke: #007bff, stroke-width: 2px;
    classDef web fill: #fff3cd, stroke: #ffc107, stroke-width: 2px;
    classDef reject fill: #f8d7da, stroke: #dc3545, stroke-width: 2px;
    class CoreDomain, T_Search, T_Time core;
    class PolicyDomain, T_Info policy;
    class WebDomain, T_Weather, T_Web web;
    class OutOfScope, End_OOS reject;
```

---

### Case 1: Tra cứu quy định chung (Static RAG/System Prompt)

```mermaid
graph TD
    Start([User: Hướng dẫn thanh toán]) --> Agent[LangChain AgentExecutor]
    Agent --> LLM[LLM ReAct Loop]
    LLM --> Thought[Thought: Intent = FAQ, không cần tra cứu DB/Tool]
    Thought --> Action[Action: Không sinh JSON Tool Call]
    Action --> FinalAnswer[Final Answer: Sinh text từ System Prompt / RAG]
    FinalAnswer --> Telemetry[Ghi log: Total_Loops = 1, Tool_Calls = 0]
    Telemetry --> End([Trả kết quả: Hướng dẫn 3 bước thanh toán])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    class LLM, Thought, Action, FinalAnswer llm;
```

---

### Case 2: Giải đáp chính sách nhà xe (Simple Data Retrieval)

```mermaid
graph TD
    Start([User: Chính sách hành lý Phương Trang]) --> Agent[LangChain AgentExecutor]
    Agent --> LLM[LLM ReAct Loop]
    LLM --> Thought[Thought: Cần tìm info nhà xe Phương Trang]
    Thought --> Action[Action: Gọi get_bus_operator_info COM-101]
    Action --> Pydantic{Pydantic Schema Validation}
    Pydantic -->|Hợp lệ| ExecuteTool[Đọc file operators.json]
    ExecuteTool --> Obs[Observation: Tối đa 20kg ký gửi...]
    Obs --> LLM
    LLM --> FinalAnswer[Final Answer: Trình bày chi tiết hành lý]
    FinalAnswer --> End([Trả kết quả cho User])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    classDef tool fill: #d4edda, stroke: #333, stroke-width: 2px;
    class LLM, Thought, Action, FinalAnswer llm;
    class Pydantic, ExecuteTool, Obs tool;
```

---

### Case 3: Đặt xe phức tạp (Complex Multi-step & Error Recovery)

```mermaid
graph TD
    Start([User: Xe HN-SaPa ngày mai, giá rẻ]) --> Agent[LangChain AgentExecutor]
%% Bước 1
    Agent --> T1[Thought 1: Lấy ngày giờ hiện tại] --> A1[Action: get_current_datetime]
    A1 --> O1[Obs 1: 2024-04-10] --> Agent
%% Bước 2: Lỗi
    Agent --> T2[Thought 2: Tìm xe] --> A2[Action: search_bus_schedules max_price='rẻ']
    A2 --> P2{Pydantic Val}
    P2 -->|LỖI: max_price phải là int| Fallback[System Inject Fallback Error]
    Fallback -.->|Retry Loop| Agent
%% Bước 3: Tự sửa
    Agent --> T3[Thought 3: Bỏ param lỗi] --> A3[Action: search_bus_schedules bỏ max_price]
    A3 --> P3{Pydantic Val} -->|Hợp lệ| O3[Obs 3: List xe HN-SaPa] --> Agent
    Agent --> FinalAnswer[Final Answer: Danh sách chuyến phù hợp]
    FinalAnswer --> End([Trả kết quả cho User])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    classDef tool fill: #d4edda, stroke: #333, stroke-width: 2px;
    classDef error fill: #f8d7da, stroke: #dc3545, stroke-width: 2px;
    class Agent, T1, A1, T2, A2, T3, A3, FinalAnswer llm;
    class O1, P3, O3 tool;
    class P2, Fallback error;
```

---

### Case 4: Lịch trình kết hợp Trải nghiệm (Hybrid: Internal + Weather/Web)

```mermaid
graph TD
    Start([User: Xe đi Hội An hôm nay? Thời tiết và Quán ăn?]) --> Agent[LangChain AgentExecutor]
%% Gọi Time & Search
    Agent --> T1[Thought 1: Check giờ và tìm xe]
    T1 --> A1[Action: get_current_datetime & search_bus_schedules]
    A1 --> O1[Obs 1: Danh sách xe Đà Nẵng - Hội An] --> Agent
%% Gọi Weather
    Agent --> T2[Thought 2: Kiểm tra thời tiết Hội An]
    T2 --> A2[Action: get_route_weather]
    A2 --> O2[Obs 2: Trời nắng đẹp] --> Agent
%% Gọi Web Search
    Agent --> T3[Thought 3: Tìm quán ăn ngon]
    T3 --> A3[Action: web_search]
    A3 --> O3[Obs 3: Cơm gà Bà Buội...] --> Agent
%% Tổng hợp
    Agent --> FinalAnswer[Final Answer: Gộp lịch xe + Thời tiết + Món ăn]
    FinalAnswer --> End([Tư vấn trọn gói cho User])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    classDef tool fill: #d4edda, stroke: #333, stroke-width: 2px;
    classDef web fill: #fff3cd, stroke: #ffc107, stroke-width: 2px;
    class Agent, T1, T2, T3, FinalAnswer llm;
    class A1, A2, O1, O2 tool;
    class A3, O3 web;
```

---

### Case 5: Thiếu thông tin (Edge Case - Guardrails Short-circuit)

```mermaid
graph TD
    Start([User: Tìm cho tôi một chuyến xe]) --> Agent[LangChain AgentExecutor]
    Agent --> Thought[Thought: Cần gọi search_bus_schedules]
    Thought --> SchemaCheck{LLM tự kiểm tra Pydantic Schema}
    SchemaCheck -->|Thiếu origin và destination| ShortCircuit[Action: Dừng vòng lặp, KHÔNG gọi Tool]
    ShortCircuit --> FinalAnswer[Final Answer: Yêu cầu thêm thông tin từ User]
    FinalAnswer --> End([Trả lời: Bạn muốn đi từ đâu đến đâu?])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    classDef guardrail fill: #e2e3e5, stroke: #383d41, stroke-width: 2px;
    class Agent, Thought, FinalAnswer llm;
    class SchemaCheck, ShortCircuit guardrail;
```

---

### Case 6: Out-of-Scope (Từ chối khéo léo)

```mermaid
graph TD
    Start([User: Dạy tôi giải toán / Cổ phiếu]) --> Agent[LangChain AgentExecutor]
    Agent --> Thought[Thought: Ý định ngoài phạm vi]
    Thought --> PolicyCheck{Đối chiếu System Prompt Guardrails}
    PolicyCheck -->|Xác nhận Out of Scope| ShortCircuit[Action: Dừng vòng lặp, từ chối web_search]
    ShortCircuit --> FinalAnswer[Final Answer: Từ chối lịch sự theo template]
    FinalAnswer --> End([Trả lời: Trợ lý AI chỉ hỗ trợ đặt vé xe...])
    classDef llm fill: #f9d0c4, stroke: #333, stroke-width: 2px;
    classDef error fill: #f8d7da, stroke: #dc3545, stroke-width: 2px;
    class Agent, Thought, FinalAnswer llm;
    class PolicyCheck, ShortCircuit, End error;
```