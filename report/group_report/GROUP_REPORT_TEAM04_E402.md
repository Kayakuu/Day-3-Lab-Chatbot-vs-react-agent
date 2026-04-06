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

Mục tiêu của dự án là xây dựng một ReAct Agent có khả năng hỗ trợ người dùng tìm kiếm chuyến xe, kiểm tra giá vé và thực hiện quy trình đặt vé xe khách giữa các tỉnh thành tại Việt Nam một cách tự động thông qua ngôn ngữ tự nhiên.

- **Success Rate**: 88% trên 25 kịch bản đặt vé (từ đơn giản đến phức tạp như đổi điểm đón/trả).
- **Key Outcome**: Agent vượt trội hơn Chatbot thông thường nhờ khả năng truy cập dữ liệu chuyến xe thời gian thực. Trong khi Chatbot chỉ có thể tư vấn chung chung về các hãng xe, Agent có thể đưa ra chính xác giờ chạy, số ghế trống và giá vé cụ thể của ngày hôm nay.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
Hệ thống sử dụng vòng lặp suy luận để giải quyết các yêu cầu đa bước:
#### 2.1.1. Thought:"Người dùng muốn đi từ Hà Nội đến Hà Giang vào sáng mai. Tôi cần kiểm tra các chuyến xe còn vé trong khung giờ 6h-10h sáng."
#### 2.1.2. Action: Gọi tool check_current_time, get_bus_schedules để tính thời gian tương đối và check số lượng vé còn trống.
#### 2.1.3. Observation: Danh sách 5 chuyến xe từ các nhà xe (Bằng Phấn, Mạnh Quân...) kèm giá vé.
#### 2.1.4. Final Answer: Tổng hợp và đề xuất chuyến xe phù hợp nhất cho khách hàng.

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `get_bus_schedules` | `origin, dest, date` | Tìm kiếm các chuyến xe khả dụng giữa hai tỉnh thành. |
| `check_seat_availability` | `trip_id` | Kiểm tra số ghế trống trong chuyến xe. |
| `calculate_total_price` | `trip_id, quantity` | Tính toán tổng tiền cho chuyến xe. |
| `get_location_coords` | `address_string` | Xác định tọa độ điểm đón/trả để tính khoảng cách di chuyển. |

### 2.3 LLM Providers Used
- **Primary**: Chat GPT 4o (Xử lý chính nhờ khả năng hiểu ngữ cảnh tiếng Việt tốt và latency thấp).
- **Secondary (Backup)**: Gemini 2.5 Flash (Xử lý backup khi có lỗi xảy ra).
- **Local**: Qwen 2.5 (Xử lý backup khi có lỗi xảy ra).

---

## 3. Telemetry & Performance Dashboard

*Analyze the industry metrics collected during the final test run.*

- **Average Latency (P50)**: 2,100ms (Do phải đợi phản hồi từ hệ thống tra cứu chuyến xe).
- **Max Latency (P99)**: 4,500ms (Khi người dùng thay đổi ý định nhiều lần trong một phiên chat)..
- **Average Tokens per Task**: 550 tokens (ReAct tiêu tốn nhiều token hơn do lưu trữ lịch sử suy luận).
- **Total Cost of Test Suite**: $0.005.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study: Lỗi xử lý hành trình đa chặng (Multi-leg Journey)
- **Input**: "Tôi muốn đi từ Sài Gòn ra Hà Nội, nhưng hãy đặt cho tôi làm 2 chặng: đầu tiên là Sài Gòn đi Đà Nẵng, sau đó từ Đà Nẵng đi Hà Nội."
- **Observation**: 
- ***Kịch bản A:*** Agent bị rối loạn thực thể (Entity Confusion). Nó truyền tham số vào Tool là origin="Sài Gòn", dest="Hà Nội" và bỏ qua chặng trung gian Đà Nẵng.
- ***Kịch bản B:*** Agent gọi Tool thành công cho chặng 1 (Sài Gòn - Đà Nẵng) nhưng sau đó đưa ra Final Answer ngay lập tức mà không tiếp tục thực hiện chặng 2 (Đà Nẵng - Hà Nội).
- **Root Cause**: 
- ***1***. Thiếu cơ chế Task Decomposition: System Prompt hiện tại đang định nghĩa một yêu cầu của người dùng tương ứng với một hành động gọi Tool duy nhất. Agent chưa đủ khả năng tự phân rã một câu lệnh phức tạp thành một danh sách các nhiệm vụ con (Sub-tasks) để thực hiện tuần tự.
- ***2***. Giới hạn về Quản lý Trạng thái (State Management): Agent không có bộ nhớ tạm để lưu trữ "kế hoạch dài hạn". Sau khi nhận được kết quả (Observation) từ chặng 1, nó có xu hướng kết thúc vòng lặp ReAct thay vì kiểm tra xem còn phần nào trong yêu cầu gốc chưa được giải quyết hay không.
- **Solution**: 
- ***1***. Prompt Enhancement: Cập nhật System Prompt với kỹ thuật Chain-of-Thought, yêu cầu Agent phải liệt kê rõ các chặng cần đi trước khi gọi Tool (Ví dụ: "Bước 1: Tìm xe chặng SG-ĐN; Bước 2: Tìm xe chặng ĐN-HN").
- ***2***. Logic Refinement: Thêm một bước kiểm tra cuối vòng lặp (Validation Step) để Agent tự đối chiếu lại câu trả lời với yêu cầu ban đầu của người dùng trước khi đưa ra Final Answer.
- ***3***. State Management: Thêm các biến trạng thái (state variables) để Agent có thể lưu trữ thông tin về các chặng đã tìm kiếm và các hành động đã thực hiện.
---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt không có ví dụ vs Prompt Few-Shot
- **Result**: Prompt có sẵn các ví dụ về đặt vé xe giúp Agent giảm tình trạng "bịa" ra giá vé (Hallucination) tới 50%.

### Experiment 2 (Bonus): Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| "Xe nào đi Đà Lạt rẻ nhất?" | Trả lời chung chung các hãng. | Liệt kê bảng giá thực tế hôm nay. | Agent |
| "Hủy vé đã đặt như thế nào?" | Trả lời đúng quy định chung. | Kiểm tra mã vé và thực hiện lệnh hủy. | Agent |
| "Chào buổi sáng" | Trả lời thân thiện. | Trả lời thân thiện + Hỏi nhu cầu đi lại. | Draw |

---

## 6. Production Readiness Review

*Considerations for taking this system to a real-world environment.*

- **Security**: Áp dụng Rate Limiting để ngăn chặn việc spam đặt vé ảo (Fake bookings) làm ảnh hưởng đến Database nhà xe.
- **Guardrails**: Thiết lập bước Human-in-the-loop: Agent chỉ thực hiện lệnh thanh toán/đặt chỗ cuối cùng sau khi người dùng xác nhận bằng nút bấm hoặc câu lệnh "Xác nhận".
- **Scaling**: 
- ***1***. Sử dụng hàng đợi (Queue) để xử lý nhiều yêu cầu Agent cùng lúc, giảm tải cho hệ thống.
- ***2***. Chuyển sang kiến trúc LangGraph để xử lý các luồng nghiệp vụ phức tạp như: Đang đặt vé thì khách muốn quay lại đổi ngày đi, hoặc hủy vé, hoặc thay đổi số lượng vé...

---

> Link GIT: https://github.com/Kayakuu/Day-3-Lab-Chatbot-vs-react-agent