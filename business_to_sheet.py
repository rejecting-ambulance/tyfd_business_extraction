import os
import re
import fitz
import pandas as pd
import tkinter as tk
from tkinter import filedialog



def pdf_to_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""

    for i, page in enumerate(doc):
        text = page.get_text("text")
        
        full_text += f"--- 第 {i + 1} 頁 ---\n{text}\n"
    return full_text

# 定義函數：處理單個 PDF 文件並提取內容
def extract_pdf_text(pdf_path, config):

    exclude_path = config.get("exclude_path", "exclude_numbers.txt")

    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_set = set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        exclude_set = set()


    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 正則處理前，保留換行符，後續匹配跨行內容
    normalized_text = extracted_text

    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：([^\n]+)"
    unified_id_pattern = r"\b\d{8}\b(?!@)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, extracted_text)
    unified_ids = re.findall(unified_id_pattern, normalized_text)
    subject_match = re.search(subject_pattern, normalized_text, re.DOTALL)
    
    filtered_unified_id = [
        num for num in unified_ids
        if not (re.fullmatch(r"\d{8}", num) and num in exclude_set)
    ]

    # 賦值內容
    dispatch_number = dispatch_number_match.group(1).strip() if dispatch_number_match else "未匹配"
    serial_number = serial_number_match.group(1).strip() if serial_number_match else "未匹配"
    original = original_match.group(1).strip() if original_match else "未匹配"
    #unified_ids_result = ", ".join(unified_ids) if unified_ids else "無"
    unified_ids_result = ", ".join(sorted(set(filtered_unified_id))) if filtered_unified_id else "無"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"

    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "8碼編號": unified_ids_result,
        "場所名稱": original,
        "場所地址": "桃園市",
        "查詢編號": "",
        "備註": subject
    }

# 定義函數：處理資料夾內的所有 PDF 並輸出到 Excel
def process_folder(folder_path, output_excel, config):
    # 搜索資料夾內的所有 PDF 文件
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]

    # 依檔名排序（不含路徑，只看檔案名稱）
    pdf_files.sort(key=lambda x: os.path.basename(x))

    # 提取每個 PDF 文件的數據
    extracted_data = [extract_pdf_text(pdf_file, config) for pdf_file in pdf_files]

    # 將結果保存為 Excel 文件
    df = pd.DataFrame(extracted_data)

    # ============================
    # ⭐ 插入第一欄「編號」
    # ============================
    df.insert(0, "編號", range(1, len(df) + 1))

    df.to_excel(output_excel, index=False)
    print(f"提取結果已保存至：{output_excel}")
    os.startfile(output_excel)

# 🖼 GUI：選取資料夾
def select_folder_gui():
    root = tk.Tk()
    root.withdraw()  # 隱藏主視窗

    folder = filedialog.askdirectory(
        title="選取 PDF 所在的資料夾"
    )

    root.destroy()

    if not folder:
        print("❌ 未選取資料夾，程式中止。")
        return None

    return folder



if __name__ == "__main__":
    folder_path = select_folder_gui()

    if folder_path:
        output_excel = "business_extraction.xlsx"
        process_folder(folder_path, output_excel, config={})