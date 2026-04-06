# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Nguyễn Đình Hiếu]
- **Student ID**: [2A202600143]
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

- **Modules Implementated**:
  - `src/agent/agent.py`: Hoàn thiện vòng lặp ReAct (Thought → Action → Observation → Final Answer), parse `Action`, execute tool động, và ghi telemetry/logs cho từng bước.
  - `run_agent.py`: Viết runner để chạy agent end-to-end, load `.env`, kiểm tra key, chọn model OpenAI hợp lệ, và “wrap” tools hiện có (`src/tools/bank_tools.py`, `src/tools/calculate.py`) thành tool spec cho agent.

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