# calculate.py

def calculate_savings_interest(principal: float, rate_percent: float, months: int) -> str:
    """
    Công cụ tính tiền lãi gửi tiết kiệm ngân hàng (lãi đơn nhận cuối kỳ).
    
    Args:
        principal (float): Số tiền gốc gửi vào (VNĐ). Ví dụ: 200000000.
        rate_percent (float): Lãi suất năm (%). Ví dụ: 4.6 (lấy từ bảng lãi suất).
        months (int): Số tháng gửi (kỳ hạn). Ví dụ: 12.
        
    Returns:
        str: Chuỗi văn bản báo cáo chi tiết số tiền lãi và tổng tiền nhận được.
    """
    try:
        # Ép kiểu dữ liệu để phòng trường hợp LLM truyền nhầm string
        principal = float(principal)
        rate_percent = float(rate_percent)
        months = int(months)

        if principal <= 0 or rate_percent < 0 or months <= 0:
            return "Lỗi: Số tiền gốc, lãi suất và số tháng phải lớn hơn 0."

        # Công thức tính lãi cuối kỳ chuẩn: 
        # Lãi = Gốc * (Lãi suất / 100) * (Số tháng / 12)
        interest_earned = principal * (rate_percent / 100) * (months / 12)
        total_amount = principal + interest_earned

        # Format số tiền kiểu Việt Nam (ví dụ: 1.000.000 thay vì 1,000,000)
        def format_vnd(amount):
            return "{:,.0f}".format(amount).replace(',', '.')

        # Chuỗi kết quả trả về cho Agent đọc và tổng hợp
        result = (
            f"[BÁO CÁO TÍNH TOÁN]\n"
            f"- Tiền gốc: {format_vnd(principal)} VNĐ\n"
            f"- Lãi suất áp dụng: {rate_percent}%/năm\n"
            f"- Kỳ hạn gửi: {months} tháng\n"
            f"=> Tiền lãi sinh ra: {format_vnd(interest_earned)} VNĐ\n"
            f"=> TỔNG TIỀN NHẬN CUỐI KỲ (Gốc + Lãi): {format_vnd(total_amount)} VNĐ"
        )
        return result

    except ValueError:
         return "Lỗi: Agent truyền sai định dạng dữ liệu. Yêu cầu truyền số thuần túy (không chứa chữ hoặc ký tự tiền tệ)."
    except Exception as e:
        return f"Lỗi hệ thống khi tính toán: {str(e)}"

# ========================================================
# CẤU HÌNH TOOL SPEC CHO AGENT
# ========================================================
CALCULATE_INTEREST_TOOL = {
    "name": "calculate_savings_interest",
    "description": (
        "Sử dụng công cụ này để tính tiền lãi tiết kiệm ngân hàng một cách chính xác. "
        "Yêu cầu 3 tham số: 'principal' (tiền gốc, chỉ nhập số, không chữ), "
        "'rate_percent' (lãi suất năm %, ví dụ 4.5), và 'months' (số tháng gửi)."
    ),
    "function": calculate_savings_interest
}

# ========================================================
# CODE TEST (Chạy trực tiếp file này để kiểm tra)
# ========================================================
if __name__ == "__main__":
    print("=== BẮT ĐẦU TEST CÔNG CỤ TÍNH TOÁN ===\n")
    
    # Giả lập LLM truyền dữ liệu vào sau khi đã cào được mức 4.6% cho 12 tháng
    tien_goc = 250000000  # 250 triệu
    lai_suat = 4.6
    ky_han = 12
    
    print(f"Giả lập: Tính lãi cho {tien_goc} VNĐ, lãi suất {lai_suat}%, kỳ hạn {ky_han} tháng...\n")
    
    ket_qua = calculate_savings_interest(
        principal=tien_goc, 
        rate_percent=lai_suat, 
        months=ky_han
    )
    
    print(ket_qua)
    print("\n=== HOÀN THÀNH TEST ===")