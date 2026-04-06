Dưới đây là mô tả chuẩn hóa cho toàn bộ các công cụ (tools) của bạn, được viết theo đúng cấu trúc và định dạng mà bạn
yêu cầu để tối ưu hóa cho LLM Agent.

### 1. Tool: `search_bus_schedules`

*Sử dụng trong: Tra cứu lịch trình, tìm chuyến xe, lọc xe theo yêu cầu*

* **Mục đích:** Tìm kiếm và lọc các chuyến xe khả dụng trong file `bus_schedules.json` dựa trên nhiều tiêu chí cùng một
  lúc (thay thế cho các tool nhỏ lẻ kiểm tra giá, chỗ trống, loại xe).
* **Input (Pydantic Schema):**
    * `origin` (String, Required): Điểm xuất phát.
    * `destination` (String, Required): Điểm đến.
    * `departure_date` (String, Optional): Ngày khởi hành mong muốn (định dạng YYYY-MM-DD).
    * `max_price` (Integer, Optional): Mức giá tối đa mà người dùng chấp nhận.
    * `vehicle_type` (String, Optional): Loại xe yêu cầu (VD: "Sleeper", "Limousine", "Standard").
    * `min_available_seats` (Integer, Optional): Số lượng ghế trống tối thiểu cần đặt.
* **Output:** Danh sách các đối tượng JSON chứa các chuyến xe thỏa mãn toàn bộ điều kiện. VD:
  `[{"id": "VN-003", "price": 241000, "departure_time": "...", ...}]`
* **Fallback Handling (Xử lý lỗi):**
    * *Không có chuyến xe phù hợp:* Trả về Observation:
      `"Không tìm thấy chuyến xe nào khớp với toàn bộ các tiêu chí. Hãy thông báo cho người dùng và gợi ý họ thay đổi giờ đi, loại xe hoặc mức giá."`
    * *Thiếu origin hoặc destination:* Trả về Observation:
      `"Lỗi: Thiếu điểm đi hoặc điểm đến. Hãy hỏi lại người dùng muốn đi từ đâu đến đâu."`

---

### 2. Tool: `get_bus_operator_info`

*Sử dụng trong: Trả lời câu hỏi về chính sách nhà xe, hành lý, tiện ích*

* **Mục đích:** Truy xuất thông tin chi tiết của một nhà xe cụ thể từ file `operators.json` dựa trên mã công ty.
* **Input (Pydantic Schema):**
    * `company_id` (String, Required): Mã ID của nhà xe (VD: "COM-101").
* **Output:** Chuỗi JSON chứa thông tin chi tiết. VD:
  `{"name": "Phương Trang", "cancellation_policy": "...", "luggage_allowance": "...", "amenities": [...]}`
* **Fallback Handling (Xử lý lỗi):**
    * *Mã công ty không tồn tại:* Trả về Observation:
      `"Lỗi: Mã nhà xe '{company_id}' không tồn tại trong hệ thống. Hãy kiểm tra lại thông tin chuyến xe."`

---

### 3. Tool: `get_current_datetime`

*Sử dụng trong: Lọc xe đã chạy, hiểu ngữ cảnh thời gian thực (hôm nay, ngày mai)*

* **Mục đích:** Lấy ngày và giờ thực tế hiện tại theo múi giờ Việt Nam để làm mốc thời gian chuẩn. **Agent luôn phải gọi
  tool này trước** nếu người dùng nhắc đến "hôm nay", "sắp tới" hoặc "bây giờ".
* **Input (Pydantic Schema):** * *(Không yêu cầu tham số)*
* **Output:** Chuỗi ngày giờ hiện tại. VD: *"2024-04-10 14:30:00"*.
* **Fallback Handling (Xử lý lỗi):**
    * *Lỗi hệ thống không lấy được giờ:* Trả về Observation:
      `"Lỗi: Không thể lấy được thời gian hệ thống. Hãy yêu cầu người dùng cung cấp cụ thể ngày giờ họ muốn đi thay vì nói 'hôm nay'."`

---

### 4. Tool: `get_route_weather`

*Sử dụng trong: Tư vấn điều kiện thời tiết cho chuyến đi*

* **Mục đích:** Truy xuất thông tin thời tiết hiện tại và dự báo ngắn hạn cho một địa điểm cụ thể (điểm đi hoặc điểm
  đến), giúp AI tư vấn loại xe (ví dụ: trời mưa nên đi xe giường nằm thay vì ghế ngồi).
* **Input (Pydantic Schema):**
    * `location` (String, Required): Tên thành phố hoặc tỉnh thành (VD: "Đà Lạt", "Sa Pa").
    * `date` (String, Optional): Ngày cần xem dự báo (YYYY-MM-DD). Mặc định là hôm nay nếu để trống.
* **Output:** Chuỗi thông tin thời tiết. VD: *"Nhiệt độ 18°C, trời có mưa phùn, đường trơn trượt."*
* **Fallback Handling (Xử lý lỗi):**
    * *Lỗi không tìm thấy địa danh:* Trả về Observation:
      `"Lỗi: Không tìm thấy dữ liệu thời tiết cho '{location}'. Hãy thông báo cho người dùng không thể kiểm tra thời tiết lúc này."`
    * *Lỗi API Timeout:* Trả về Observation:
      `"Lỗi gián đoạn kết nối với trạm thời tiết. Bỏ qua thông tin thời tiết và tiếp tục hỗ trợ đặt vé."`

---

### 5. Tool: `web_search`

*Sử dụng trong: Trả lời các câu hỏi phụ trợ, thông tin du lịch ngoài hệ thống*

* **Mục đích:** Tìm kiếm thông tin thực tế trên Internet cho các câu hỏi không nằm trong `bus_schedules.json` (ví dụ: "
  Từ bến xe Đà Lạt ra chợ đêm bao xa?", "Đèo Hải Vân hôm nay có cấm đường không?").
* **Input (Pydantic Schema):**
    * `query` (String, Required): Từ khóa hoặc câu hỏi cần tìm kiếm.
* **Output:** Đoạn trích dẫn thông tin tóm tắt từ kết quả tìm kiếm.
* **Fallback Handling (Xử lý lỗi):**
    * *Không có kết quả trả về:* Trả về Observation:
      `"Không tìm thấy thông tin trên mạng cho truy vấn này. Hãy báo cho người dùng rằng bạn chỉ là trợ lý đặt vé và không có thông tin ngoài luồng này."`
    * *Lỗi mạng/API:* Trả về Observation:
      `"Lỗi kết nối công cụ tìm kiếm. Hãy xin lỗi người dùng và khuyên họ tự tra cứu trên Google."`