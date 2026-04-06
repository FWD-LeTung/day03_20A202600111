import os
import re
import json
import time
import streamlit as st
from typing import List, Dict, Any, Optional
from openai import OpenAI
from tavily import TavilyClient

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TAVILY_API_KEY = ""   # lấy tại tavily.com
OPENAI_API_KEY = ""   # lấy tại platform.openai.com

# ─────────────────────────────────────────────
# TOOL: Tavily Search
# ─────────────────────────────────────────────
def tavily_search(query: str, max_results: int = 5) -> str:
    """Search real-time web data using Tavily."""
    client = TavilyClient(api_key=TAVILY_API_KEY)
    results = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
    )
    snippets = []
    for r in results.get("results", []):
        title   = r.get("title", "")
        content = r.get("content", "")
        url     = r.get("url", "")
        snippets.append(f"[{title}] {content}\nNguồn: {url}")
    return "\n\n".join(snippets) if snippets else "Không tìm thấy kết quả."


# ─────────────────────────────────────────────
# LLM PROVIDER (thin wrapper around OpenAI)
# ─────────────────────────────────────────────
class LLMProvider:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self._client    = OpenAI(api_key=OPENAI_API_KEY)

    def generate(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        t0 = time.time()
        resp = self._client.chat.completions.create(
            model=self.model_name,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt},
            ],
        )
        latency_ms = int((time.time() - t0) * 1000)
        content    = resp.choices[0].message.content or ""
        return {
            "content":    content,
            "provider":   "openai",
            "model_name": self.model_name,
            "usage":      dict(resp.usage) if resp.usage else {},
            "latency_ms": latency_ms,
        }


# ─────────────────────────────────────────────
# REACT AGENT
# ─────────────────────────────────────────────
class ReActAgent:
    """
    ReAct-style agent: Thought → Action → Observation → … → Final Answer
    """

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
    ):
        self.llm       = llm
        self.tools     = tools
        self.max_steps = max_steps
        self.trace: List[Dict[str, Any]] = []   # exposed for UI

    # ── System prompt ──────────────────────────────────────────────
    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )
        return f"""
Bạn là một Chuyên gia Phân tích Chiến lược Tài chính cấp cao. Bạn có khả năng tra cứu thông tin thị trường theo thời gian thực.

CÁC CÔNG CỤ CÓ SẴN:
{tool_descriptions}

ĐỊNH DẠNG PHẢN HỒI (BẮT BUỘC TUÂN THEO):
Thought: <lập luận của bạn>
Action: tool_name({{"query": "...", "max_results": 5}})
Observation: <kết quả công cụ trả về>
... (lặp lại nếu cần)
Final Answer: <câu trả lời cuối cùng>

QUY TẮC DỰ BÁO BẮT BUỘC:
1. KHÔNG trả lời chung chung. PHẢI chọn xu hướng cụ thể: TĂNG, GIẢM hoặc ĐI NGANG.
2. PHẢI đưa ra con số dự báo cụ thể (VD: "Lãi suất VCB kỳ hạn 12 tháng dự kiến đạt 6.2% - 6.5% trong quý tới").
3. CĂN CỨ LUẬN ĐIỂM:
   - Tỷ giá USD/VND > 25.000 → Dự báo TĂNG lãi suất để giữ nội tệ.
   - Lạm phát (CPI) > 4%      → Dự báo TĂNG lãi suất để thắt chặt tiền tệ.
   - Ngân hàng TMCP đã tăng   → Dự báo Big4 sẽ tăng theo sau ~1 tháng.
4. Phong cách: Quyết đoán, chuyên nghiệp.
5. Khi gọi công cụ, tham số PHẢI là JSON hợp lệ, không dùng markdown hay backtick.
6. Sau khi có đủ dữ liệu, kết thúc bằng "Final Answer:" và dừng lại.
"""

    # ── Main loop ──────────────────────────────────────────────────
    def run(self, user_input: str) -> str:
        self.trace = []
        system_prompt  = self.get_system_prompt()
        current_prompt = user_input.strip()
        steps = 0

        while steps < self.max_steps:
            result  = self.llm.generate(current_prompt, system_prompt=system_prompt)
            content = (result.get("content") or "").strip()

            # Check for Final Answer
            final = self._extract_final_answer(content)
            if final is not None:
                self.trace.append({"type": "final", "content": final})
                return final

            # Extract & execute action
            action = self._extract_action(content)
            if action is None:
                self.trace.append({"type": "raw", "content": content})
                return content or "Không có phản hồi."

            tool_name, raw_args = action
            thought_match = re.search(r"Thought\s*:\s*(.*?)(?:Action\s*:|$)", content, re.DOTALL)
            thought_text  = thought_match.group(1).strip() if thought_match else ""

            self.trace.append({
                "type":    "step",
                "step":    steps + 1,
                "thought": thought_text,
                "action":  f"{tool_name}({raw_args})",
            })

            observation = self._execute_tool(tool_name, raw_args)

            self.trace.append({
                "type":        "observation",
                "step":        steps + 1,
                "tool":        tool_name,
                "observation": observation,
            })

            current_prompt = (
                f"{current_prompt}\n\n{content}\nObservation: {observation}\n"
            )
            steps += 1

        return "Final Answer: Không thể hoàn thành trong giới hạn bước. Vui lòng thu hẹp câu hỏi."

    # ── Tool execution ─────────────────────────────────────────────
    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                fn = tool.get("func")
                if not callable(fn):
                    return f"Tool {tool_name} không thể gọi được."
                try:
                    parsed = self._parse_tool_args(args)
                    if isinstance(parsed, dict):
                        return str(fn(**parsed))
                    if isinstance(parsed, list):
                        return str(fn(*parsed))
                    return str(fn(parsed))
                except TypeError as e:
                    return f"Lỗi tham số: {e}"
                except Exception as e:
                    return f"Lỗi thực thi: {type(e).__name__}: {e}"
        return f"Không tìm thấy tool '{tool_name}'."

    # ── Parsers ────────────────────────────────────────────────────
    def _extract_action(self, text: str) -> Optional[tuple]:
        matches = re.findall(
            r"Action\s*:\s*([a-zA-Z0-9_]+)\((.*)\)\s*$", text, flags=re.MULTILINE | re.DOTALL
        )
        if matches:
            tool_name, raw = matches[-1]
            return tool_name.strip(), raw.strip()
        m = re.search(r"^\s*([a-zA-Z0-9_]+)\((.*)\)\s*$", text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None

    def _extract_final_answer(self, text: str) -> Optional[str]:
        m = re.search(
            r"Final Answer\s*:\s*(.*)\s*$", text, flags=re.IGNORECASE | re.DOTALL
        )
        return m.group(1).strip() if m else None

    def _parse_tool_args(self, raw: str) -> Any:
        s = (raw or "").strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except Exception:
            pass
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s


# ─────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="AI Financial ReAct Agent", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

:root {
  --bg:        #0a0c10;
  --surface:   #111318;
  --border:    #1e2230;
  --accent:    #00e5a0;
  --accent2:   #0077ff;
  --warn:      #ff6b35;
  --text:      #e8eaf0;
  --muted:     #6b7280;
  --thought:   #1a1f2e;
  --obs:       #0f1a14;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text);
  font-family: 'Syne', sans-serif;
}

[data-testid="stSidebar"] { display: none; }

.block-container { max-width: 860px; margin: 0 auto; padding: 2rem 1.5rem 6rem; }

h1 { font-size: 1.9rem; font-weight: 800; letter-spacing: -0.03em; color: var(--accent); margin-bottom: 0.2rem; }

.subtitle { color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; margin-bottom: 2rem; }

/* Chat bubbles */
.msg-user {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px 12px 4px 12px;
  padding: 0.9rem 1.1rem;
  margin: 1rem 0 0.4rem auto;
  max-width: 80%;
  font-size: 0.93rem;
}

.msg-assistant {
  background: linear-gradient(135deg, #0d1f16 0%, #0a1020 100%);
  border: 1px solid #1a3a28;
  border-left: 3px solid var(--accent);
  border-radius: 4px 12px 12px 12px;
  padding: 1rem 1.2rem;
  margin: 0.4rem 0 1rem;
  max-width: 92%;
  font-size: 0.93rem;
  line-height: 1.65;
}

/* Trace blocks */
.trace-block {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  border-radius: 8px;
  padding: 0.7rem 1rem;
  margin: 0.35rem 0;
}
.trace-thought  { background: var(--thought); border-left: 3px solid var(--accent2); color: #a0b4d8; }
.trace-action   { background: #1a1200; border-left: 3px solid #f5a623; color: #e8c97a; }
.trace-obs      { background: var(--obs); border-left: 3px solid var(--accent); color: #7ecfa8; }

.label {
  font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em;
  opacity: 0.55; margin-bottom: 0.25rem;
}

/* Input */
[data-testid="stChatInput"] textarea {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
  border-radius: 10px !important;
}

.tip-box {
  background: #101820;
  border: 1px solid #1a2840;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font-size: 0.82rem;
  color: #6fa8d4;
  margin-top: 0.4rem;
  font-family: 'IBM Plex Mono', monospace;
}
.tip-box span { color: var(--accent2); font-weight: 600; }

.verdict-up   { color: var(--accent); font-weight: 700; }
.verdict-down { color: var(--warn);   font-weight: 700; }
.verdict-flat { color: #aaa;          font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1>📈 AI Financial ReAct Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">// Thought → Action → Observation → Final Answer</p>', unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "traces" not in st.session_state:
    st.session_state.traces = []

# Render past messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f'<div class="msg-user">🧑‍💼 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        # Show trace if available
        if i // 2 < len(st.session_state.traces):
            trace = st.session_state.traces[i // 2]
            with st.expander("🔍 Chi tiết ReAct trace", expanded=False):
                for item in trace:
                    if item["type"] == "step":
                        if item.get("thought"):
                            st.markdown(
                                f'<div class="trace-block trace-thought">'
                                f'<div class="label">💭 Thought — step {item["step"]}</div>{item["thought"]}</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f'<div class="trace-block trace-action">'
                            f'<div class="label">⚡ Action — step {item["step"]}</div>{item["action"]}</div>',
                            unsafe_allow_html=True,
                        )
                    elif item["type"] == "observation":
                        short = item["observation"][:400] + ("…" if len(item["observation"]) > 400 else "")
                        st.markdown(
                            f'<div class="trace-block trace-obs">'
                            f'<div class="label">📡 Observation — step {item["step"]}</div>{short}</div>',
                            unsafe_allow_html=True,
                        )
        st.markdown(f'<div class="msg-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("VD: Dự báo lãi suất VCB kỳ hạn 12 tháng tháng 5/2026..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="msg-user">🧑‍💼 {prompt}</div>', unsafe_allow_html=True)

    # Build agent on each call (stateless)
    tools = [
        {
            "name":        "tavily_search",
            "description": "Tìm kiếm thông tin tài chính, lãi suất, tỷ giá, lạm phát theo thời gian thực từ web.",
            "func":        tavily_search,
        }
    ]
    llm   = LLMProvider(model_name="gpt-4o")
    agent = ReActAgent(llm=llm, tools=tools, max_steps=5)

    with st.status("🧠 Agent đang suy luận…", expanded=True) as status:
        st.write("🔎 Bước 1: Thu thập dữ liệu thị trường thực tế…")
        answer = agent.run(prompt)
        st.write("✅ Hoàn tất phân tích.")
        status.update(label="✅ Phân tích hoàn tất", state="complete")

    # Save trace
    st.session_state.traces.append(agent.trace)

    # Show trace
    with st.expander("🔍 Chi tiết ReAct trace", expanded=True):
        for item in agent.trace:
            if item["type"] == "step":
                if item.get("thought"):
                    st.markdown(
                        f'<div class="trace-block trace-thought">'
                        f'<div class="label">💭 Thought — step {item["step"]}</div>{item["thought"]}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="trace-block trace-action">'
                    f'<div class="label">⚡ Action — step {item["step"]}</div>{item["action"]}</div>',
                    unsafe_allow_html=True,
                )
            elif item["type"] == "observation":
                short = item["observation"][:400] + ("…" if len(item["observation"]) > 400 else "")
                st.markdown(
                    f'<div class="trace-block trace-obs">'
                    f'<div class="label">📡 Observation — step {item["step"]}</div>{short}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown(f'<div class="msg-assistant">{answer}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Verdict tip
    low = answer.lower()
    if "tăng" in low:
        st.markdown(
            '<div class="tip-box"><span>▲ XU HƯỚNG TĂNG</span> — Cân nhắc chốt gói tiết kiệm sau 1–2 tuần '
            'để hưởng mức lãi mới cao hơn.</div>',
            unsafe_allow_html=True,
        )
    elif "giảm" in low:
        st.markdown(
            '<div class="tip-box"><span>▼ XU HƯỚNG GIẢM</span> — Nên chốt gói tiết kiệm ngay hôm nay '
            'trước khi lãi suất hạ nhiệt.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="tip-box"><span>→ ĐI NGANG</span> — Thị trường ổn định, theo dõi thêm '
            'trong 2–4 tuần tới.</div>',
            unsafe_allow_html=True,
        )
