# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Tien Huy Hoang
- **Student ID**: 2A202600486
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

Trong bài Lab này, tôi chịu trách nhiệm chính trong việc xây dựng hệ thống dữ liệu mẫu (Mock Data) để phục vụ cho việc kiểm thử Agent.

- **Modules Implementated**: 
    - `data/bus_schedules.json`: Xây dựng tập dữ liệu với hơn 100 bản ghi chuyến xe, bao gồm các trường thông tin chi tiết như mã chuyến, nhà xe, điểm đi/đến, giá vé và loại xe.
    - `data/operators.json`: Thiết lập thông tin chi tiết về các nhà xe, chính sách hoàn vé và tiện ích đi kèm.
- **Code Highlights**:
    ```json
    {
      "id": "VN-001",
      "company_id": "COM-103",
      "origin": "Đà Lạt",
      "destination": "TP.HCM",
      "price": 302000,
      "available_seats": 17,
      "vehicle_type": "Xe ghế ngồi (Standard)"
    }
    ```
- **Documentation**: Tôi đã chuẩn hóa định dạng địa danh (VD: luôn dùng "TP.HCM" thay vì các tên biến thể) để đảm bảo Agent có thể tìm kiếm chính xác nhiệm vụ lọc dữ liệu từ JSON. Tôi cũng thiết kế các trường dữ liệu biên (Edge cases) như chuyến xe có 0 ghế trống để kiểm tra khả năng xử lý của Agent.

---

## II. Debugging Case Study (10 Points)

Trong quá trình chạy thử nghiệm, tôi phát hiện Agent không thể tìm thấy chuyến xe mặc dù dữ liệu có tồn tại.

- **Problem Description**: Khi người dùng hỏi "Tìm xe đi Sài Gòn", Agent gọi tool `search_bus_schedules(destination="Sài Gòn")` nhưng nhận được kết quả trống.
- **Log Source**: `logs/2026-04-06.log`
    - `Action: search_bus_schedules(origin="Hà Nội", destination="Sài Gòn")`
    - `Observation: Không tìm thấy chuyến xe nào khớp với toàn bộ các tiêu chí.`
- **Diagnosis**: Trong file `bus_schedules.json`, tôi sử dụng tên chuẩn là "TP.HCM". Tuy nhiên, dữ liệu mock chưa có cơ chế mapping giữa các tên gọi khác nhau của cùng một địa điểm (Sài Gòn vs TP.HCM).
- **Solution**: Tôi đã bổ sung thêm các biến thể tên gọi vào tài liệu hướng dẫn trong `SYSTEM_PROMPT` và cập nhật dữ liệu mock để bao quát các cách gọi phổ biến, giúp Agent thông minh hơn trong việc nhận diện địa điểm.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Dựa trên kết quả thực hiện lab, tôi rút ra các nhận xét về sự khác biệt giữa hai mô hình:

1.  **Reasoning**: Khối `Thought` giúp Agent phân rã câu hỏi phức tạp. Ví dụ, khi hỏi "Xe nào rẻ nhất đi Đà Lạt mà không mưa?", Agent biết phải: (1) Check thời tiết -> (2) Tìm xe -> (3) So sánh giá. Chatbot thông thường thường bỏ qua yếu tố thời tiết hoặc trả lời chung chung.
2.  **Reliability**: Agent chạy tệ hơn Chatbot ở các câu hỏi mang tính chất tư vấn cảm tính hoặc ngoài lề, vì nó cố gắng "ép" mình vào quy trình gọi tool, gây ra độ trễ (latency) cao không cần thiết.
3.  **Observation**: Kết quả từ `Observation` đóng vai trò là "mỏ neo" sự thật. Nếu tool báo hết ghế, Agent lập tức thay đổi chiến thuật gợi ý nhà xe khác thay vì hứa hẹn bừa bãi như Chatbot thuần túy.

---

## IV. Future Improvements (5 Points)

Để hệ thống Agent này đạt chuẩn Production, tôi đề xuất các hướng cải tiến:

- **Scalability**: Sử dụng **Vector Database** (như Qdrant hoặc ChromaDB) để lưu trữ `operators.json` và `bus_schedules.json` nếu số lượng chuyến xe lên đến hàng triệu, giúp tra cứu theo ngữ nghĩa thay vì chỉ filter cứng.
- **Safety**: Áp dụng cơ chế **Human-in-the-loop** cho bước `book_ticket` cuối cùng để đảm bảo khách hàng xác nhận lại thông tin trước khi hệ thống trừ tiền thật.
- **Performance**: Triển khai **Asynchronous Tool Calling** để Agent có thể kiểm tra thời tiết ở cả điểm đi và điểm đến cùng một lúc, giảm tổng thời gian chờ đợi của người dùng.

---

> [!NOTE]
> Báo cáo này được tự động gợi ý dựa trên các đóng góp thực tế trong dự án. Bạn hãy điền thêm Student ID và chỉnh sửa lại nội dung nếu cần thiết trước khi nộp bài.
