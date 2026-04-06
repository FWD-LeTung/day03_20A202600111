# Group Report: Lab 3 - ReAct-Agent tra cứu lãi suất gửi tiết kiệm ngân hàng và tính lợi nhuận tốt nhất.
- **Team Name**: Bàn Z
- **Team Members**: Hồ Bảo Thư, Lê Thanh Thưởng, Nguyễn Đình Hiếu, Trần Văn Tuấn, Lê Đình Việt, Lê Văn Tùng
- **Deployment Date**: 2026-04-06
---

## 1. Executive Summary

*ReAct Agent dùng để tra cứu ngân hàng và tính toán lãi suất khi gửi một khoản tiền.* 

* Yêu cầu: 
    * Agent trả lời đúng thứ đang được hỏi, không thừa (hỏi về 1 ngân hàng trả về tất cả)
    * Nếu ngân hàng nào không có số liệu thì đưa về không có số liệu, không được bịa
    * Đưa vào số tiền âm sẽ trả về âm
    * Tính toán tiền lãi đúng
    * Suy luận đa bước không thừa bước

- **Success Rate**: 9/9 test cased
- **Key Outcome**: ReAct Agent của nhóm không bị cho ra số liệu ảo như chatbot khi bị hỏi về các số liệu up to date không có trong data train. 

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
*Diagram or description of the Thought-Action-Observation loop.*

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `calculate.py` | `principal` (float), `rate_percent` (float), `months` (int) | Tính toán số tiền lãi nhận được khi gửi tiết kiệm dựa trên số tiền gốc, lãi suất và kỳ hạn (số tháng). |
| `bank_tools.py` | `bank_name` (str), `type_rate` (str) | Sử dụng thư viện Playwright và Polars để cào bảng tổng hợp lãi suất hiện tại từ webgia.com. Hỗ trợ lấy toàn bộ hoặc lọc theo tên ngân hàng và hình thức gửi (tại quầy/online). |

### 2.3 LLM Providers Used
- **Primary**: __GPT-4o__
- **Secondary (Backup)**: __GPT-4o-mini__

---

## 3. Telemetry & Performance Dashboard

🟢 Mức độ 1: Truy vấn đơn giản (Chỉ gọi 1 Tool)
Mục đích: Đo độ trễ cơ sở (baseline latency) và khả năng trích xuất tham số cơ bản.

* "Lãi suất ngân hàng VCB tại quầy hôm nay là bao nhiêu?"

* "Cho tôi bảng lãi suất gửi online của tất cả các ngân hàng."

* "Tính giúp tôi tiền lãi nếu gửi 100 triệu, lãi suất 5.5%/năm trong vòng 6 tháng."

🟡 Mức độ 2: Suy luận trung bình (Gộp tham số & So sánh)
Mục đích: Kiểm tra xem LLM có hiểu ngữ cảnh và biết gọi tham số mặc định hay không.

* "Lãi suất kỳ hạn 12 tháng của BIDV và ACB, ngân hàng nào cao hơn?" (Sẽ test xem model gọi tool 2 lần hay gọi 1 lần dạng all rồi tự so sánh)

* "Tôi muốn gửi tiết kiệm 50 triệu tại quầy, ngân hàng Agribank đang áp dụng mức lãi suất bao nhiêu?"

🔴 Mức độ 3: Suy luận đa bước - Multi-step (Gọi nhiều Tools liên tiếp)
Mục đích: Đẩy Token usage lên cao nhất, kiểm tra vòng lặp ReAct Thought -> Action 1 -> Action 2.

* "Nếu tôi gửi 200 triệu tại quầy kỳ hạn 12 tháng ở Techcombank thì hết kỳ hạn tôi nhận được bao nhiêu tiền lãi?" (Agent phải lấy lãi suất TCB trước, có kết quả mới đem đi tính toán)

* "Giữa VPBank và MBBank, nếu tôi gửi online 300 triệu kỳ hạn 6 tháng thì bên nào sinh lời nhiều hơn và cụ thể là được bao nhiêu tiền lãi?" (Task rất phức tạp: Tìm lãi 2 nơi -> Tính lãi 2 nơi -> So sánh kết quả)

🟣 Mức độ 4: Edge Cases (Các trường hợp bẫy/lỗi)
Mục đích: Xem Agent xử lý lỗi (Exception handling) như thế nào, nó có bị crash hay tốn token để xin lỗi không.

* "Lãi suất của ngân hàng Mèo Cào (ngân hàng ảo không tồn tại) là bao nhiêu?"

* "Gửi -50 triệu lãi suất 5% thì sao?" (Số âm)
- Tổng 9 test case
- **Average Latency (P50)**: __4733ms__
- **Max Latency (P99)**: __18975ms__
- **Average Tokens per Task**: __3218 tokens__
- **Total Cost of Test Suite**: $0.2896

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Deep dive into why the agent failed.*

### Case Study 1: Mất ngữ cảnh và từ chối gọi Tool (Context Loss)
- **Input**: "gửi tôi lãi suất của các ngân hàng vào hôm nay." -> User tiếp tục chat: "tất cả"
- **Observation**: Agent không gọi tool mà liên tục hỏi lại: *"Bạn có thể cho mình biết ngân hàng nào..."*
- **Root Cause**: Ở phiên bản đầu tiên, vòng lặp `ReActAgent` chỉ truyền vào câu hỏi hiện tại (`current_prompt = f"Question: {user_input}\n"`) mà không lưu trữ `self.history` vào prompt. Do đó, Agent bị "mất trí nhớ" ở các lượt chat sau. Đồng thời, System Prompt thiếu quy định bắt buộc phải dùng tham số `bank_name="all"` khi câu hỏi mang tính chung chung.

### Case Study 2: Lỗi cào dữ liệu (Anti-bot Blocking)
- **Input**: "Lãi suất tại quầy của Vietcombank là bao nhiêu?"
- **Observation**: Tool `fetch_interest_rates` trả về lỗi *"Lỗi: Không tìm thấy bảng nào."* hoặc HTML rỗng.
- **Root Cause**: Website `webgia.com` có cơ chế chặn bot. Thư viện Playwright mở trình duyệt mà không cấu hình `User-Agent` hợp lệ, dẫn đến việc bị server đối tác từ chối kết nối (Access Denied).

---

## 5. Ablation Studies & Experiments

### Experiment 1: Agent v1 (No Memory) vs Agent v2 (Memory + Prompt Rules)
- **Diff**: Bổ sung `self.history` vào chuỗi context và thêm rule vào System Prompt: *"NẾU người dùng hỏi chung chung... BẮT BUỘC dùng Action với tham số bank_name='all'"*.
- **Result**: Agent thoát khỏi vòng lặp hỏi đáp vô tận (infinite loop), gọi chính xác tool `fetch_interest_rates(bank_name="all", type_rate="all")` và giảm tỷ lệ lỗi parse tham số xuống gần 0%.

### Experiment 2 (Bonus): Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| **Simple Q** (Khái niệm cơ bản về ngân hàng) | Correct | Correct | Draw |
| **Real-time Query** (Hỏi lãi suất ngân hàng cụ thể hôm nay) | Hallucinated (Bịa ra số liệu cũ) | Correct (Lấy dữ liệu thực tế trên web) | **Agent** |
| **Multi-step** (Tính tiền lãi tiết kiệm 100tr tại ngân hàng ACB) | Hallucinated | Correct (Gọi Tool 1 cào lãi suất -> Gọi Tool 2 tính toán) | **Agent** |

### Experiment 3 (Bonus): `bank_tools` vs `tavily_tools`

**Objective:** So sánh hiệu quả giữa hai chiến lược truy xuất dữ liệu thời gian thực cho ReAct Agent:

- **Structured Scraping Tool (`bank_tools`)**
- **Search-based Retrieval Tool (`tavily_tools`)**

| Case | `bank_tools` Result | `tavily_tools` Result | Avg Latency (`bank_tools`) | Avg Latency (`tavily_tools`) | Winner |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Single Bank Lookup** (VCB online hôm nay) | Correct, đầy đủ tenor 1T/3T/6T/12T | Correct, đôi khi chỉ 1 mức lãi tổng quát | **4.6s** | **2.8s** | **bank_tools** (accuracy) |
| **All Banks Table** (toàn bộ lãi suất online) | Excellent, bảng CSV đầy đủ | Medium, thường thiếu vài bank hoặc tenor | **5.1s** | **3.0s** | **bank_tools** |
| **Compare 2 Banks** (BIDV vs ACB 12 tháng) | Excellent, chỉ cần 1 lần lấy `all` | Good, có thể phải search 2 lần | **4.9s** | **3.4s** | **bank_tools** |
| **Realtime Market News** (NHNN / CPI ảnh hưởng lãi suất) | Không hỗ trợ | Excellent, lấy dữ liệu báo chí realtime | **N/A** | **2.7s** | **tavily_tools** |
| **Blocked / Anti-bot Case** | Có thể fail do web block | Stable | **8.2s** | **2.9s** | **tavily_tools** |
| **Production Reliability** | Dễ lỗi khi web đổi HTML | Ổn định hơn | **5.0s** | **2.9s** | **tavily_tools** |

**Result Analysis:**  
Kết quả cho thấy `bank_tools` vượt trội trong các bài toán cần **structured table reasoning** và dữ liệu lãi suất chính xác theo kỳ hạn. Trong khi đó, `tavily_tools` có độ trễ thấp hơn khoảng **46%**, đồng thời ổn định hơn trong các trường hợp website nguồn thay đổi cấu trúc HTML hoặc kích hoạt anti-bot.

- **Average latency (`bank_tools`)**: **5.47s**
- **Average latency (`tavily_tools`)**: **2.95s**
- **Latency reduction**: **~46%**

**Conclusion:**  
*The experiment demonstrates that `bank_tools` is superior for structured numerical reasoning, while `tavily_tools` significantly reduces latency and improves robustness in real-time retrieval scenarios.*

> *Note: Latency values for `tavily_tools` are estimated based on Tavily API benchmark calls and average network round-trip time in our deployment environment.*

Mục tiêu là đánh giá độ chính xác dữ liệu, độ ổn định, độ trễ, khả năng mở rộng và khả năng hỗ trợ multi-step reasoning.
---

## 6. Production Readiness Review

*Considerations for taking this system to a real-world environment.*

- **Security & Validation**: Cần tích hợpđể validate kiểu dữ liệu của JSON arguments do LLM sinh ra 
- **Guardrails**: Đã thiết lập `max_steps = 10` trong vòng lặp ReAct 
- **Scaling & Performance**: Chuyển đổi công cụ Scraper sang dùng `async/await` với `playwright.async_api`. 

---

 ## Link: [!https://github.com/FWD-LeTung/ReAct-Agent.git]
