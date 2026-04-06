# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Trần Văn Tuấn ]
- **Student ID**: [2A202600498]
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

- **Modules Implementated**:
  - `src/agent/agent.py`: Hoàn thiện vòng lặp ReAct (Thought → Action → Observation → Final Answer), parse `Action`, execute tool động, và ghi telemetry/logs cho từng bước.
  - `run_agent.py`: Viết runner để chạy agent end-to-end, load `.env`, chọn model OpenAI hợp lệ, và bọc tích hợp các tools: `bank_tools`, `calculate`. Tại phiên bản V2, tiếp tục tích hợp thêm `tavily_search` và `predict_future_rate`.
  - `src/tools/tavily_search.py`: Module tìm kiếm internet mở rộng bằng Tavily API.
  - `src/tools/predictor.py`: Mô-đun dự báo (Predictor) dùng Machine Learning (mock XGBoost/LSTM/LLM-RAG) để đưa ra dự đoán lãi suất (Version 2).

- **Code Highlights**:
  - **ReAct Loop + Telemetry**:
    - Agent gọi `llm.generate(...)`, log `AGENT_STEP`, log metric `LLM_METRIC` (prompt/completion tokens, latency) và lưu `TOOL_OBSERVATION`.
    - Có `max_steps` để tránh vòng lặp vô hạn và có nhánh thoát khi tìm thấy `Final Answer:`.
  - **Action parsing & tool execution**:
    - Parse được format `Action: tool_name(...)`.
    - Tool args ưu tiên JSON (`{"a":1}`) và có fallback xử lý chuỗi.
  - **Runner ổn định môi trường**:
    - Do `.env` từng để `DEFAULT_MODEL=gemini-...` (không chạy được trên OpenAI), runner tự nhận biết và chuyển về `gpt-4o` để tránh lỗi 404 `model_not_found`.
    - Không yêu cầu thay đổi cấu trúc `src/tools/`; runner bọc trực tiếp 2 tool:
      - `fetch_interest_rates` (crawl bảng lãi suất từ webgia)
      - `calculate` (tính tiền lãi/tiền nhận được)

- **Documentation (agent ↔ tools)**:
  - `run_agent.py` tạo danh sách tools (name/description/func) đưa vào `ReActAgent`.
  - `src/agent/agent.py` dùng `tool['name']` để map sang `tool['func']` và feed `Observation` ngược lại prompt để agent quyết định bước tiếp theo.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  - Khi hỏi “tìm ngân hàng có lãi suất cao nhất…”, agent đã gọi tool `fetch_interest_rates` nhưng tool trả về lỗi do Playwright chưa tải browser:
    - `BrowserType.launch: Executable doesn't exist ... Please run: playwright install`

- **Log Source**:
  - `logs/2026-04-06.log` có các event:
    - `AGENT_STEP` chứa lệnh tool call:
      - `Action: fetch_interest_rates({"bank_name":"all","type_rate":"all"})`
    - `TOOL_OBSERVATION` chứa lỗi Playwright yêu cầu `playwright install`

- **Diagnosis**:
  - Đây là **lỗi môi trường/runtime dependency** (Playwright cần cài browser binaries) chứ không phải lỗi prompt.
  - Agent vẫn làm đúng cơ chế ReAct: gọi tool để lấy dữ liệu “thế giới thật”, nhưng tool thất bại nên Observation trả lỗi.

- **Solution**:
  - Hướng xử lý:
    1. Chạy `playwright install` để tool có browser executable.
    2. (Nếu cần production-ready) thêm failure-handling: khi Observation báo thiếu browser, agent trả hướng dẫn cài hoặc fallback sang nguồn khác.
  - Kết quả: sau khi môi trường đáp ứng, tool `fetch_interest_rates` có thể trả CSV và agent có thể tiếp tục phân tích để chọn “lãi suất cao nhất”.

*(Ngoài ra mình cũng gặp case lỗi cấu hình model: `.env` để `DEFAULT_MODEL=gemini-...` khiến OpenAI trả 404. Runner đã tự sửa bằng cách fallback về `gpt-4o` và log cảnh báo.)*

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning (Thought block)**:
   - Chatbot thường “trả lời ngay” theo suy luận nội bộ và dễ bịa số liệu khi cần tra cứu.
   - ReAct tách rõ: khi thiếu dữ liệu thì **Action gọi tool**, lấy Observation rồi mới kết luận, giúp quá trình giải quyết bài toán “tìm lãi suất → tính tiền lãi” trở nên có thể kiểm chứng.

2. **Reliability (khi Agent tệ hơn Chatbot)**:
   - Khi tool/infra lỗi (vd. Playwright thiếu browser), Agent có thể thất bại hoặc trả lời vòng vo hơn chatbot.
   - Với câu hỏi đơn giản (chào hỏi/giải thích khái niệm), chatbot nhanh hơn và ít điểm hỏng hơn (không phụ thuộc tool).

3. **Observation ảnh hưởng bước tiếp theo**:
   - Observation là “sự thật môi trường”. Nếu Observation rỗng/lỗi, agent phải:
     - đổi chiến lược (tool khác), hoặc
     - hướng dẫn người dùng sửa môi trường, hoặc
     - kết thúc có điều kiện.
   - Thực tế logs cho thấy agent quyết định bước tiếp theo dựa hoàn toàn vào Observation (thành công thì tính lãi, thất bại thì không thể suy ra “ngân hàng tốt nhất”).

---

## IIIb. Version 2 - Agent Dự báo (Predictor) & Tích hợp Tavily Search

- **Mục tiêu**: Nâng cấp chức năng của agent lên phiên bản 2 bằng cách:
  1. **Agent Dự báo (Predictor)**: Sử dụng các mô hình học máy (như LSTM, XGBoost hoặc thậm chí là LLM với kỹ thuật RAG) để đưa ra con số dự đoán.
  2. **Mở rộng tra cứu với Tavily Search**: Thu hẹp khoảng cách kiến thức tĩnh, giúp agent có thể tra cứu tin tức thời sự trên internet một cách tự chủ, làm dữ kiện cho mô hình hoặc cập nhật thông tin mới nhất.
- **Log Cuộc gọi mẫu (Minh hoạ gọi Tavily)**:
  ```text
  You: Hãy tìm tin tức mới nhất về biến động lãi suất ngân hàng hôm nay giúp tôi.
  
  Assistant:
  Thought: Câu hỏi này cần thông tin cập nhật hằng ngày, tôi không có sẵn trong hệ thống nên phải chủ động tìm kiếm tin tức bên ngoài. Tôi sẽ gọi công cụ tavily_search.
  Action: tavily_search({"query": "tin tức biến động lãi suất tiết kiệm ngân hàng hôm nay mới nhất", "max_results": 3})
  
  Observation:
  Title: Lãi suất tiết kiệm đồng loạt giảm...
  URL: https://...
  Content: Ngay trong sáng nay, một số ngân hàng lớn đồng thuận giảm lãi suất tiết kiệm...
  
  Final Answer: Theo thông tin mới nhất hiện nay trên Internet, tình hình lãi suất tiết kiệm đang có diễn biến giảm tại một số ngân hàng lớn. Bạn có thể cho tôi biết dự định gửi tiền của bạn để tính cụ thể được không?
  ```
  *(Quá trình này được ghi nhận đầy đủ qua các sự kiện `AGENT_START`, `AGENT_STEP`, và `TOOL_OBSERVATION` tại log. Thể hiện tính đúng đắn của vòng lặp ReAct khi áp dụng mở rộng Tool mới)*

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Tách tool execution sang async worker (queue) để không block vòng lặp agent.
  - Chuẩn hoá output tool thành JSON schema để agent parse ổn định hơn (tránh “CSV string” quá dài).

- **Safety**:
  - Thêm guardrails cho tool call: validate args (kiểu dữ liệu, giới hạn) trước khi chạy tool.
  - Thêm cơ chế retry/backoff và “tool timeout” rõ ràng.

- **Performance**:
  - Cache kết quả crawling theo ngày (vì lãi suất không đổi theo từng giây).
  - Giảm token bằng cách cắt prompt/history và chỉ đưa Observation cần thiết vào step kế tiếp.