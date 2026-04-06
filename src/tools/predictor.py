import random

def predict_future_rate(bank_name: str, duration: int, model_type: str = "xgboost") -> str:
    """
    Sử dụng mô hình học máy (mock) để dự đoán lãi suất trong tương lai.
    """
    model_type = model_type.lower()
    if model_type not in ["lstm", "xgboost", "llm-rag"]:
        model_type = "xgboost"
        
    # Tạo số liệu giả lập dự đoán (trend: giảm nhẹ hoặc giữ nguyên)
    trend = random.choice(["giảm nhẹ", "tăng nhẹ", "đi ngang"])
    change_pct = round(random.uniform(0.1, 0.3), 2)
    
    if trend == "giảm nhẹ":
        prediction = f"Mô hình {model_type.upper()} dự báo lãi suất của {bank_name} kỳ hạn {duration} tháng sẽ {trend} khoảng {change_pct}% trong quý tới."
    elif trend == "tăng nhẹ":
        prediction = f"Mô hình {model_type.upper()} dự báo lãi suất của {bank_name} kỳ hạn {duration} tháng sẽ {trend} khoảng {change_pct}% trong quý tới."
    else:
        prediction = f"Mô hình {model_type.upper()} dự báo lãi suất của {bank_name} kỳ hạn {duration} tháng sẽ có xu hướng {trend} trong thời gian tới."
        
    return prediction
