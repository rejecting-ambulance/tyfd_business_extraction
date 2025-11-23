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
def extract_business_info(pdf_path, config):

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
        "統一編號": unified_ids_result,
        "場所名稱": original,
        "場所地址": "桃園市",
        "備註": subject
    }

def extract_clinic_info(pdf_path):
    """
    從文件文字中解析：機構名稱、機構代碼、機構地址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    #print(cleaned)
    # ---- 正規表示式 ----
    name_pattern = r"機構名稱[:：]\s*([^\s:：()（）]+)"
    code_pattern = r"機構代碼[:：]\s*([A-Za-z0-9]{10})"

    # ⭐ 地址解析：抓到下一個(項目) 或 字串結尾為止
    # 可完整捕捉「號」「樓」「－」「之」「及」等字串
    #addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\s*(?:\(\s*五\s*\)|五[、.]))"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=機構電話)"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    code_match = re.search(code_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = None
    if addr_match:
        address = addr_match.group(1).strip()
        address = address[:-3]

    # 共通提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    subject_match = re.search(subject_pattern, extracted_text, re.DOTALL)

    # 賦值內容
    dispatch_number = dispatch_number_match.group(1).strip() if dispatch_number_match else "未匹配"
    serial_number = serial_number_match.group(1).strip() if serial_number_match else "未匹配"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"


    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": "無",
        "場所名稱": name_match.group(1).strip() if name_match else None,
        "場所地址": address,
        "備註": f"{subject}\n機構代碼: {code_match.group(1).strip()}" if code_match else "機構代碼: 未匹配",
    }

def extract_cram_school_info(pdf_path):
    """
    從文件文字中解析：補習班名、斑址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    # ---- 正規表示式 ----
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+補習班(?:[\u4e00-\u9fff\d\w]*分班)?"

    # 地址解析：班址~，桃園市開頭
    addr_pattern = r"(班址[\s\S]*?(桃園市[^\n,，]*))"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)


    # 共通提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    subject_match = re.search(subject_pattern, extracted_text, re.DOTALL)

    # 賦值內容
    dispatch_number = dispatch_number_match.group(1).strip() if dispatch_number_match else "未匹配"
    serial_number = serial_number_match.group(1).strip() if serial_number_match else "未匹配"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"


    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": "無",
        "場所名稱": name_match.group(0).strip() if name_match else None,
        "場所地址": addr_match.group(2).strip() if addr_match else None,
        "備註": subject
    }


def extract_kindergarten_info(pdf_path):
    """
    從文件文字中解析：幼兒園班名、班址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    # ---- 正規表示式 ----
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+幼兒園(?:[\u4e00-\u9fff\d\w]*分班)?"

    # 地址解析：班址~，桃園市開頭
    addr_pattern = r"(?:園址|班址)[:：]\s*(桃園市[^\n\)）。,]*[^\s\)）。,]*(?:號[^\s\)）。,]*)?)[\)）。,。]"



    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    name = name_match.group(0).strip() if name_match else None
    name = f'桃園市{name}' if name else None
    address = addr_match.group(1).strip() if addr_match else None


    # 共通提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點
    original_pattern = r"正本：([^\n]+)"

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    subject_match = re.search(subject_pattern, extracted_text, re.DOTALL)
    original_match = re.search(original_pattern, extracted_text)

    # 賦值內容
    dispatch_number = dispatch_number_match.group(1).strip() if dispatch_number_match else "未匹配"
    serial_number = serial_number_match.group(1).strip() if serial_number_match else "未匹配"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"
    original = original_match.group(1).strip() if original_match else "未匹配"

    if "幼兒園" in original:
        name = original
    
    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": "無",
        "場所名稱": name,
        "場所地址": address,
        "備註": subject
    }


# 定義函數：處理資料夾內的所有 PDF 並輸出到 Excel
def process_folder(folder_path, output_excel, config):
    # 搜索資料夾內的所有 PDF 文件
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]

    # 依檔名排序（不含路徑，只看檔案名稱）
    pdf_files.sort(key=lambda x: os.path.basename(x))


    
    extracted_data = []
    for pdf_file in pdf_files:

        first_text = pdf_to_text(pdf_file).strip()  # 只讀取前 100 個字元判斷類型
        #print(first_text)
        
        # 選擇路線：機構 or 商業
        if "機構代碼" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 醫事機構")
            data = extract_clinic_info(pdf_file)
        elif "補習班" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 補習班")
            data = extract_cram_school_info(pdf_file)        
        elif "幼兒園" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 幼兒園")
            data = extract_kindergarten_info(pdf_file)        
        else:
            print(f"▶ {os.path.basename(pdf_file)} → (分)公司及商業")
            data = extract_business_info(pdf_file, config)

        extracted_data.append(data)
    

    # 提取每個 PDF 文件的數據
    #extracted_data = [extract_business_info(pdf_file, config) for pdf_file in pdf_files]

    # 測試提取函數
    #extracted_data = [extract_cram_school_info(pdf_file) for pdf_file in pdf_files]

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