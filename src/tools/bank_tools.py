import pandas as pd
import polars as pl
import io
import re
from playwright.sync_api import sync_playwright

def extract_number(text):
    """Hàm lọc số chuẩn hóa và chia cho 100 (Dành cho Python String)"""
    text_str = str(text).strip().lower()
    if pd.isna(text) or text_str in ['-', '', 'nan', 'none']:
        return "-"
        
    text_str = text_str.replace("web giá", "").replace("webgiá.com", "").replace("webgia.com", "")
    text_str = text_str.replace("xem tại", "").strip()

    match = re.search(r"(\d+[\.,]\d+|\d+)", text_str)
    if match:
        num_str = match.group(1).replace(',', '.')
        try:
            val = float(num_str) / 100
            return str(round(val, 2))
        except ValueError:
            return "-"
    return "-"

def process_table(pd_df, hinh_thuc):
    """Hàm phụ trợ xử lý từng bảng đơn lẻ sử dụng Polars"""
    if isinstance(pd_df.columns, pd.MultiIndex):
        pd_df.columns = [str(col[-1]).strip() for col in pd_df.columns]
    else:
        pd_df.columns = [str(col).strip() for col in pd_df.columns]
    
    cols = list(pd_df.columns)
    cols[0] = "Ngan_hang"
    pd_df.columns = cols
    
    data_dict = {col: pd_df[col].astype(str).tolist() for col in pd_df.columns}
    df = pl.DataFrame(data_dict)
    df = df.insert_column(1, pl.lit(hinh_thuc).alias("Hinh_thuc"))
    
    term_cols = df.columns[2:]
    for col_name in term_cols:
         df = df.with_columns(
             pl.col(col_name).map_elements(extract_number, return_dtype=pl.Utf8)
         )
    return df

def fetch_interest_rates(bank_name: str = "all", type_rate: str = "all") -> str:
    url = "https://webgia.com/lai-suat/"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            html_source = page.content()
            browser.close()
            
        tables = pd.read_html(io.StringIO(html_source))
        if not tables:
            return "Lỗi: Không tìm thấy bảng nào."
            
        valid_tables = [df for df in tables if len(df.columns) >= 8]
        if len(valid_tables) == 0:
            return "Lỗi: Không tìm thấy bảng lãi suất chuẩn."
            
        processed_dfs = []
        if len(valid_tables) > 0:
            processed_dfs.append(process_table(valid_tables[0].copy(), "Tai_quay"))
        if len(valid_tables) > 1:
            processed_dfs.append(process_table(valid_tables[1].copy(), "Online"))
            
        final_df = pl.concat(processed_dfs, how="diagonal")
        final_df = final_df.fill_null("-")
        
        if type_rate.lower() == "tai_quay":
            final_df = final_df.filter(pl.col("Hinh_thuc") == "Tai_quay")
        elif type_rate.lower() == "online":
            final_df = final_df.filter(pl.col("Hinh_thuc") == "Online")
            
        if bank_name.lower() != "all":
            final_df = final_df.with_columns(
                pl.col("Ngan_hang")
                .str.replace_all(r"(?i)webgia\.com|web giá|xem tại", "")
                .str.strip_chars() 
            )

            # Lọc thông minh: Tìm chứa từ khóa
            search_key = bank_name.lower().strip()
            filtered_df = final_df.filter(
                pl.col("Ngan_hang").str.to_lowercase().str.contains(search_key)
            )

            if filtered_df.height == 0:
                # Nếu không thấy Techcombank, trả về danh sách có sẵn để Agent biết đường mà tìm lại
                available = ", ".join(final_df["Ngan_hang"].to_list()[:15])
                return f"Lỗi: Không thấy '{bank_name}'. Danh sách tham khảo: {available}"
            
            final_df = filtered_df
                
        return final_df.write_csv()
        
    except Exception as e:
        return f"Lỗi thực thi Scraper: {str(e)}"

# Cấu hình Tool Spec
BANK_SCRAPE_TOOL = {
    "name": "fetch_interest_rates",
    "description": "Lấy bảng tổng hợp lãi suất từ WebGia dạng CSV. Truyền bank_name='all' để lấy toàn bộ ngân hàng. Truyền type_rate='all' để lấy cả online và tại quầy, hoặc truyền 'tai_quay', 'online' để lọc.",
    "function": fetch_interest_rates
}

# ========================================================
# CODE TEST
# ========================================================
if __name__ == "__main__":
    print("=== BẮT ĐẦU TEST CÔNG CỤ (PLAYWRIGHT + POLARS) ===\n")
    print("Đang cào và giải mã dữ liệu... \n")
    
    csv_string = fetch_interest_rates(bank_name="all", type_rate="all")
    
    if not csv_string.startswith("Lỗi"):
        # Đọc lại CSV bằng Polars để hiển thị
        df_view = pl.read_csv(io.StringIO(csv_string))
        
        # Cấu hình Polars để in ra toàn bộ bảng đẹp mắt
        pl.Config.set_tbl_rows(100) # In tối đa 100 dòng
        pl.Config.set_tbl_cols(20)  # In tối đa 20 cột
        
        print(">> BẢNG DỮ LIỆU LÃI SUẤT TỔNG HỢP:\n")
        print(df_view)
        
    else:
        print(csv_string)
        
    print("\n=== HOÀN THÀNH TEST ===")