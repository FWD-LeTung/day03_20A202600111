import streamlit as st
import openai
from tavily import TavilyClient
import re
from tools.calculate import calculate
from tools.extract_financial_data import extract_financial_data
# --- 1. CẤU HÌNH ---
TAVILY_API_KEY = ""
OPENAI_API_KEY = ""

tavily = TavilyClient(api_key=TAVILY_API_KEY)
client = openai.OpenAI(api_key=OPENAI_API_KEY)


# --- HELPER ---
def detect_intent(text):
    text = text.lower()
    forecast_keywords = ["dự báo", "tới", "tháng tới", "quý", "sắp tới"]

    for kw in forecast_keywords:
        if kw in text:
            return "forecast"

    return "current"


def parse_user_input(text):
    amount = 100_000_000
    duration = 6

    money = re.search(r"(\d+)\s*(triệu|tr|tỷ|ty)?", text.lower())
    if money:
        value = int(money.group(1))
        unit = money.group(2)

        if unit in ["tỷ", "ty"]:
            amount = value * 1_000_000_000
        else:
            amount = value * 1_000_000

    time = re.search(r"(\d+)\s*tháng", text.lower())
    if time:
        duration = int(time.group(1))

    return amount, duration


# --- AI PREDICTION ---
def get_ai_prediction(user_input, market_data, calc_result, history):
    system_instruction = f"""
    Bạn là một Chuyên gia Phân tích Chiến lược Tài chính cấp cao. 
    DỮ LIỆU THỊ TRƯỜNG MỚI NHẤT: {market_data}
    
    QUY TẮC DỰ BÁO BẮT BUỘC:
    1. KHÔNG trả lời chung chung kiểu 'cần theo dõi thêm' hay 'tùy thuộc vào thị trường'.
    2. PHẢI chọn một xu hướng chủ đạo: TĂNG, GIẢM hoặc ĐI NGANG.
    3. PHẢI đưa ra con số dự báo cụ thể (Ví dụ: "Lãi suất VCB kỳ hạn 12 tháng dự kiến đạt mức 6.2% - 6.5% trong quý tới").
    4. CĂN CỨ LUẬN ĐIỂM: 
       - Nếu Tỷ giá USD/VND > 25.000 -> Dự báo TĂNG lãi suất để giữ nội tệ.
       - Nếu Lạm phát (CPI) > 4% -> Dự báo TĂNG lãi suất để thắt chặt tiền tệ.
       - Nếu các ngân hàng TMCP (Techcombank, VPBank) đã tăng -> Dự báo Big4 (VCB, BIDV) sẽ tăng theo sau 1 tháng.
    5. Phong cách: Quyết đoán, chuyên nghiệp, sử dụng ngôn ngữ của nhà phân tích.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_instruction}]
        + history
        + [{"role": "user", "content": user_input}],
        temperature=0.3
    )

    return response.choices[0].message.content


# --- UI ---
st.set_page_config(page_title="AI Financial Predictor", page_icon="📈")
st.title("📈 AI Predictor: Dự báo Lãi suất Chuyên sâu")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- MAIN ---
if prompt := st.chat_input("Hỏi dự báo ngân hàng cụ thể..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("📊 Đang phân tích biến số vĩ mô và dữ liệu thực tế...", expanded=True):

            # 1. Search Tavily
            search_query = f"lãi suất {prompt} mới nhất tháng 4 2026 tỷ giá USD VND lạm phát Việt Nam"
            search_context = str(
                tavily.search(
                    query=search_query,
                    max_results=5,
                    search_depth="advanced"
                )
            )
            st.write("✅ Đã cập nhật dữ liệu thị trường")

            # 2. Detect intent
            intent = detect_intent(prompt)

            # 3. Extract data
            market_data = extract_financial_data(search_context)
            rate = market_data.get("interest_rate", 6.0)

            # 4. Parse input
            amount, duration = parse_user_input(prompt)

            # 5. Calculate (REAL)
            calc_result = calculate(
                amount=amount,
                rate=rate,
                duration=duration
            )

            # 6. Logic
            if intent == "current":
                prediction = f"""
📊 KẾT QUẢ HIỆN TẠI:

- Lãi suất: {rate}%
- Tiền lãi: {calc_result["interest"]:,} VND
- Tổng tiền: {calc_result["total"]:,} VND
"""
            else:
                prediction = get_ai_prediction(
                    prompt,
                    market_data,
                    calc_result,
                    st.session_state.messages[:-1]
                )

            st.write("✅ Hoàn tất mô hình dự báo")

        st.markdown(prediction)

        st.session_state.messages.append({
            "role": "assistant",
            "content": prediction
        })

        # Gợi ý
        if "tăng" in prediction.lower():
            st.info("💡 Có thể chờ thêm để hưởng lãi cao hơn")
        elif "giảm" in prediction.lower():
            st.warning("💡 Nên gửi ngay trước khi lãi giảm")
