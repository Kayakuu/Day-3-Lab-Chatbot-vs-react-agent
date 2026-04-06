# INDIVIDUAL REPORT TEMPLATE - LAB 3: CHATBOT VS REACT AGENT

## PERSONAL INFORMATION
- **Họ và tên:** Trần Nhật Vĩ
- **MSSV:** 2A202600497
- **Nhóm:** 04
- **Vai trò trong dự án:** Workflow, Langchain, Ollama, Gemini API, Rule Base.

## I. Technical Contribution
- Thiết lập môi trường (Python, Streamlit, Ollama/Gemini API).
- Xây dựng Tool cho Agent (Search, Trip Details, Distance...).
- Triển khai ReAct Agent logic (Prompt engineering, Thought-Action-Observation loop).
- Tích hợp LLM Provider (Google Gemini hoặc Local Qwen).
- Testing và tinh chỉnh Prompt để Agent hoạt động ổn định.

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent rơi vào vòng lặp vô tận (Infinite Loop) hoặc lặp lại cùng một hành động "Thought: I need to search for..." mà không thực sự gọi Tool hoặc không thoát ra khỏi vòng lặp sau khi đã có kết quả.
- **Log Source**: Em đã bị xóa mất sau khi merge.
- **Diagnosis**: 
- ***Prompt Engineer***: System Prompt chưa đủ chặt chẽ để yêu cầu LLM nhận diện rằng thông tin trong Observation đã đủ để trả lời (Final Answer).
- ***Stop Sequences***: Model Local qua Ollama (qwen) đôi khi bỏ qua ký tự dừng, dẫn đến việc tự tạo ra các bước Thought giả lập của chính nó (Trả ra tiếng Trung)
- **Solution**: 
- ***Cập nhật lại cấu trúc Prompt trong src/agent/agent.py, thêm các ví dụ (few-shot) rõ ràng về việc khi nào nên dừng lại.***
- ***Điều chỉnh hàm parse output để xử lý ngoại lệ khi LLM trả về định dạng không đúng chuẩn ReAct.***
- ***Chuyển sang sử dụng modal gemini qua API***
---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: Khối Thought đóng vai trò là "chuỗi tư duy" (Chain of Thought). So với Chatbot trả lời trực tiếp dựa trên xác suất từ ngữ, ReAct Agent sử dụng Thought để phân rã yêu cầu phức tạp thành các bước nhỏ. Điều này giúp Agent xác định được mình "đang thiếu thông tin gì" trước khi hành động, giúp kết quả chính xác và logic hơn.
2.  **Reliability**: Em thấy Agent hoạt động kém hơn Chatbot trong các câu hỏi thông thường, mang tính hội thoại. Cấu trúc ReAct ép buộc model phải suy nghĩ và gọi tool, đôi khi nó làm phức tạp hóa vấn đề hoặc gặp lỗi định dạng, trong khi một Chatbot có thể trả lời ngay lập tức một cách tự nhiên.
3.  **Observation**: Observation đóng vai trò là "nhãn quan" của Agent vào thế giới thực. Phản hồi từ môi trường (ví dụ: kết quả từ Google Search hoặc Database) cho phép Agent tự sửa lỗi. Nếu Observation trả về "Không tìm thấy dữ liệu", Agent sẽ nhìn vào đó để thay đổi chiến thuật Thought tiếp theo thay vì bịa đặt thông tin (Hallucination).

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Chuyển đổi cơ chế gọi Tool từ đồng bộ sang Asynchronous (Asyncio). Trong thực tế, các API bên thứ ba có thể chậm; việc sử dụng hàng đợi (Queue) sẽ giúp xử lý nhiều yêu cầu Agent cùng lúc mà không làm nghẽn hệ thống.
- **Safety**: Triển khai một Guardrail Layer hoặc Supervisor LLM. Lớp này sẽ kiểm tra đầu ra của Agent để đảm bảo không vi phạm chính sách bảo mật hoặc thực hiện các hành động gây hại.
- **Performance**: Sử dụng Semantic Caching (như Redis với Vector similarity). Nếu một câu hỏi tương tự đã được Agent giải quyết với các bước Thought tương đương, hệ thống có thể trả về kết quả ngay lập tức thay vì chạy lại toàn bộ vòng lặp ReAct đắt đỏ. Sử dụng Langchain Pandas DataFrame để tăng tốc độ truy xuất dữ liệu từ database. Tối ưu truy vấn cụ thể hoặc dùng tool để giảm thiểu lượng dữ liệu cần truy xuất.
- **Cost**: Sử dụng các API miễn phí hoặc có gói miễn phí (như Google Gemini) nhằm giảm chi phí cho hệ thống.

---

> Link GIT: https://github.com/Kayakuu/Day-3-Lab-Chatbot-vs-react-agent