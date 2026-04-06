def extract_financial_data(search_data):
    prompt = f"""
    Bạn là hệ thống trích xuất dữ liệu tài chính.

    Dữ liệu:
    {search_data}

    Hãy trích xuất và trả về JSON:

    {{
        "interest_rate": số (%),
        "bank": "tên ngân hàng nếu có",
        "usd_vnd": số nếu có,
        "cpi": số nếu có
    }}

    QUY TẮC:
    - Chỉ lấy lãi suất tiền gửi (không lấy lãi vay)
    - Ưu tiên ngân hàng được nhắc trong câu hỏi
    - Nếu không chắc → null
    - Chỉ trả JSON, không giải thích
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # nhẹ, đủ dùng
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    import json
    return json.loads(response.choices[0].message.content)
