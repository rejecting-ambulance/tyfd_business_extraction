import pandas as pd
import os
import shutil

# 1. 設定 Excel 路徑和 PDF 資料夾路徑
excel_path = r"C:\Users\zhand\Downloads\code\廠登處理發布版\Please.xlsx"
pdf_folder_path = r"C:\Users\zhand\Downloads\code\廠登處理發布版\split_pdf"

# 嘗試讀取 Excel 檔案並列出所有欄位名稱
try:
    df = pd.read_excel(excel_path)  # 先讀取整個 Excel 檔案
    print("讀取成功，欄位名稱為：", df.columns.tolist())  # 列出欄位名稱，方便檢查
except Exception as e:
    print(f"讀取 Excel 發生錯誤：{e}")
    exit()

# 如果欄位名稱是中文或其他文字，請確認並替換
current_col_name = "現有檔名"  # 替換為實際的欄位名稱
new_col_name = "新檔名"  # 替換為實際的欄位名稱

# 2. 選擇需要的欄位
try:
    df = df[[current_col_name, new_col_name]]  # 讀取指定欄位
    df.columns = ["current_name", "new_name"]  # 重新命名欄位
except KeyError:
    print(f"Excel 中找不到欄位：{current_col_name} 或 {new_col_name}")
    exit()

# 3. 開始處理檔案
for current_name, new_name in zip(df["current_name"], df["new_name"]):
    # 確保檔名加上 .pdf
    current_name_pdf = f"{str(current_name).strip()}"
    new_name_pdf = f"{str(new_name).strip()}.pdf"

    current_path = os.path.join(pdf_folder_path, current_name_pdf)  # 現有檔案路徑
    new_path = os.path.join(pdf_folder_path, new_name_pdf)  # 新檔案路徑

    # 檢查現有檔案是否存在
    if os.path.exists(current_path):
        # 重新命名檔案
        os.rename(current_path, new_path)
        print(f"檔案已重新命名：{current_name_pdf} -> {new_name_pdf}")

        # 根據新檔名中的 "XX區" 建立資料夾並移動檔案
        try:
            # 提取檔名中的 "XX區"
            region = new_name.split('-')[-1].strip()  # 提取最後一段，假設格式為 "數字-名稱-XX區"
            region_folder = os.path.join(pdf_folder_path, region)  # XX區資料夾路徑

            # 如果資料夾不存在則建立
            if not os.path.exists(region_folder):
                os.makedirs(region_folder)
                print(f"已建立資料夾：{region_folder}")

            # 將檔案移動到對應資料夾
            shutil.move(new_path, os.path.join(region_folder, new_name_pdf))
            print(f"檔案已移動到資料夾：{region_folder}")

        except IndexError:
            print(f"無法從檔名中提取區域，檔案名稱：{new_name_pdf}")

    else:
        print(f"檔案不存在，無法重新命名：{current_name_pdf}")

print("檔案重新命名與分類完成！")
