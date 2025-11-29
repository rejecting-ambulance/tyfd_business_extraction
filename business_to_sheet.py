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
def extract_rest_doc_info(pdf_path, config):

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
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
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
        "備註": subject,
        "類別": "其他類別"
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
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    code_match = re.search(code_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = None
    if addr_match:
        address = addr_match.group(1).strip()
        #address = address[:-3]

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
        "類別": "醫事機構"
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
        "備註": subject,
        "類別": "補習班"
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
    addr_pattern = r"(?:園址|班址)[^桃]*?(桃園市[^\n\)）。,，]*)"


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
        "備註": subject,
        "類別": "幼兒園"
    }


def extract_after_school_info(pdf_path):
    """
    從文件文字中解析：課後照顧服務中心班名、斑址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    # ---- 正規表示式 ----
    name_pattern = r"桃園市[\u4e00-\u9fff\d\w]+課後照顧服務中心(?:[\u4e00-\u9fff\d\w]*分班)?"

    # 地址解析：班址~，桃園市開頭
    addr_pattern = r"(中心地址[\s\S]*?(桃園市[^\n,，。]*))"

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
        "備註": subject,
        "類別": "課後照顧服務中心"
    }



def extract_infant_center_info(pdf_path):
    """
    從文件文字中解析：托嬰中心班名、班址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    # ---- 正規表示式 ----
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+托嬰中心?"

    # 地址解析：班址~，桃園市開頭
    addr_pattern = r"(?:地址)[:：]桃*?(桃園市[^\n\)）。,，]*)"


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

    if "托嬰中心" in original:
        name = original
    
    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": "無",
        "場所名稱": name,
        "場所地址": address,
        "備註": subject,
        "類別": "托嬰中心"
    }

def extract_nursing_home_info(pdf_path):
    """
    從文件文字中解析：護理之家機構名稱、機構地址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    #print(cleaned)
    # ---- 正規表示式 ----
    name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ⭐ 地址解析：抓到下一個(項目) 或 字串結尾為止
    # 可完整捕捉「號」「樓」「－」「之」「及」等字串
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = None
    if addr_match:
        address = addr_match.group(1).strip()

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
        "備註": f"{subject}",
        "類別": "護理之家"
    }


def extract_longtern_care_info(pdf_path):
    """
    從文件文字中解析：長照機構機構名稱、機構地址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    #print(cleaned)
    # ---- 正規表示式 ----
    name_pattern = r"機構名稱[:：]\s*([^\s:：()（）。]+)"

    # ⭐ 地址解析：抓到下一個(項目) 或 字串結尾為止
    # 可完整捕捉「號」「樓」「－」「之」「及」等字串
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = "未匹配"
    if addr_match:
        address = addr_match.group(1).strip().rstrip("。")
        #address = address[:-3]

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
        "備註": f"{subject}",
        "類別": "長照機構"
    }


# 定義函數：處理單個 PDF 文件並提取內容
def extract_concern_industry_info(pdf_path, config):

    '''
    擷取：治安顧慮行業/自治條例行業名稱、地址、統編
    '''

    exclude_path = config.get("exclude_path", "exclude_numbers.txt")
    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_set = set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        exclude_set = set()


    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取
    normalized_text = extracted_text.replace("\r", "").replace("\n", "").replace(" ", "")

    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
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
    unified_ids_result = ", ".join(unified_ids) if unified_ids else "無"
    unified_ids_result = ", ".join(sorted(set(filtered_unified_id))) if filtered_unified_id else "無"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"

    # 名稱：函准~統一前
    name_pattern = r"國稅局函准(.+?)統一"
    name_match = re.search(name_pattern, normalized_text)
    if name_match:
        name = name_match.group(1).strip()
        # 去掉末尾多餘的左括號
        if name.endswith("（"):
            name = name[:-1].strip()
    else:
        name = "未匹配"

    # 統編：統一編號：~、
    unified_id_pattern = r"統一編號[:：](\d+)[、,]"
    unified_id_match = re.search(unified_id_pattern, normalized_text)
    unified_id = unified_id_match.group(1).strip() if unified_id_match else "未匹配"

    # 地址：公司地址：~最後一個)
    address_pattern = r"公司地址[:：]([^\)）]+)[\)）]"
    address_match = re.search(address_pattern, normalized_text)
    address = address_match.group(1).strip() if address_match else "未匹配"


    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": unified_id,
        "場所名稱": f"{name}",
        "場所地址": f"{address}",
        "備註": subject,
        "類別": "自治條例行業(資訊休閒、治安顧慮等)"
    }


def extract_branch_info(pdf_path, config):

    '''
    擷取：公司、分公司名稱、地址、公司分公司統編
    '''

    exclude_path = config.get("exclude_path", "exclude_numbers.txt")

    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_set = set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        exclude_set = set()


    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取
    normalized_text = extracted_text.replace("\r", "").replace("\n", "").replace(" ", "")

    branch_pattern = r"申請(?:.*?所屬|在)?([\s\S]*?分公司)"
    branch_match = re.search(branch_pattern, normalized_text)
    branch_name = branch_match.group(1).strip() if branch_match else "未匹配"
    
    addr_pattern = r"(?:公司所在地|公司地址|新地址)[^桃]*?(桃園市[^\n\)）。,，;；]*)(?:[\)）。,，;；]|$)"

    addr_match = re.findall(addr_pattern, normalized_text)
    #address = addr_match.group(1).strip() if addr_match else None

    if addr_match:
        # 若找到多個，用第二次（或最後一次）
        if len(addr_match) >= 2:
            address = addr_match[1].strip()
        else:
            address = addr_match[0].strip()
    else:
        address = "未匹配"

    if "（" in address:
        address = f'{address}）'
    elif "(" in address:
        address = f'{address})'

    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：.*?([\u4e00-\u9fff\d\w]+公司)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
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
    unified_ids_result = ", ".join(unified_ids) if unified_ids else "無"
    unified_ids_result = ", ".join(sorted(set(filtered_unified_id))) if filtered_unified_id else "無"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"

    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": unified_ids_result,
        #"場所名稱": f"{original}<>{branch_name}",
        "場所名稱": f"{original}{branch_name}",
        "場所地址": f"{address}",
        "備註": subject,
        "類別": "分公司"
    }

# 定義函數：處理單個 PDF 文件並提取內容
def extract_business_info(pdf_path, config):

    '''
    擷取：商業名稱、地址、統編
    '''

    exclude_path = config.get("exclude_path", "exclude_numbers.txt")

    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_set = set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        exclude_set = set()


    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取
    normalized_text = extracted_text.replace("\r", "").replace("\n", "").replace(" ", "")

    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
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
    unified_ids_result = ", ".join(unified_ids) if unified_ids else "無"
    unified_ids_result = ", ".join(sorted(set(filtered_unified_id))) if filtered_unified_id else "無"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"

    pattern = r"^(?P<name>[^\[（\(]+).*?\[\s*(?P<addr>[^\]]+)\s*\]"

    m = re.search(pattern, original)

    original = m.group("name").strip() if m else "未匹配"
    addr = m.group("addr").strip() if m else "未匹配"


    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": unified_ids_result,
        "場所名稱": f"{original}",
        "場所地址": f"{addr}",
        "備註": subject,
        "類別": "商業"
    }


def extract_company_info(pdf_path, config):

    '''
    擷取：公司名稱、地址、公司分公司統編
    '''

    exclude_path = config.get("exclude_path", "exclude_numbers.txt")

    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            exclude_set = set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        exclude_set = set()


    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取
    normalized_text = extracted_text.replace("\r", "").replace("\n", "").replace(" ", "")


    addr_pattern = r"(?:公司所在地|公司地址|新地址|所在地為)[^桃]*?(桃園市[^\n。,，;；]*)(?:[。,，;；]|$)"

    addr_match = re.search(addr_pattern, normalized_text)
    address = addr_match.group(1).strip() if addr_match else "未匹配"


    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：.*?([\u4e00-\u9fff\d\w]+公司)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
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
    unified_ids_result = ", ".join(unified_ids) if unified_ids else "無"
    unified_ids_result = ", ".join(sorted(set(filtered_unified_id))) if filtered_unified_id else "無"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"

    match = re.search(r"(.+?)代理人：", original)
    if match:
        original = match.group(1).strip()

    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": unified_ids_result,
        "場所名稱": f"{original}",
        "場所地址": f"{address}",
        "備註": subject,
        "類別": "公司"
    }


def extract_other_health_info(pdf_path):
    """
    從文件文字中解析：其他衛福機構名稱、機構地址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    #print(cleaned)
    # ---- 正規表示式 ----
    name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ⭐ 地址解析：抓到下一個(項目) 或 字串結尾為止
    # 可完整捕捉「號」「樓」「－」「之」「及」等字串
    #addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\s*(?:\(\s*五\s*\)|五[、.]))"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"

    # ---- 搜尋 ----
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = "未匹配"
    if addr_match:
        address = addr_match.group(1).strip()
    
    name = "未匹配"
    if name_match:
        name = name_match.group(1).strip()

    if name[-1] == "。":
        name = name[:-1]
    if address[-1] == "。":
        address = address[:-1]


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
        "場所名稱": name,
        "場所地址": address,
        "備註": f"{subject}",
        "類別": "其他衛福機構"
    }


def extract_hostel_info(pdf_path):
    """
    從文件文字中解析：民宿名稱、地址
    並處理跨行地址、全形括號、中文標點
    """

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 先把換行符號移除，避免地址被切斷
    cleaned = extracted_text.replace("\n", "").replace("\r", "")
    
    # ---- 正規表示式 ----
    addr_pattern = r"地址[:：]\s*([^\s:：()（）。]+)"

    # ---- 搜尋 ----
    addr_match = re.findall(addr_pattern, cleaned)

    # ---- 處理地址 ----
    address = "未匹配"
    if addr_match:
        address = addr_match[-1].strip()     # 取最後一個結果

    # 共通提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點
    original_pattern = r"正本：([\s\S]*?)(?=副本)"

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    subject_match = re.search(subject_pattern, extracted_text, re.DOTALL)
    original_match = re.search(original_pattern, cleaned)

    # 賦值內容
    dispatch_number = dispatch_number_match.group(1).strip() if dispatch_number_match else "未匹配"
    serial_number = serial_number_match.group(1).strip() if serial_number_match else "未匹配"
    subject = subject_match.group(1).strip().replace("\n", "") if subject_match else "未匹配"
    original = original_match.group(1).strip() if original_match else "未匹配"

    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": serial_number,
        "發文字號": dispatch_number,
        "統一編號": "無",
        "場所名稱": original,
        "場所地址": address,
        "備註": f"{subject}",
        "類別": "觀傳事業機構"
    }


# 定義函數：處理單個 PDF 文件並提取內容
def extract_pawnshop_info(pdf_path):
    '''
    擷取：當鋪名稱、地址、統編      
    '''

    extracted_text = pdf_to_text(pdf_path)  # 使用 fitz 處理，確保文本完整提取

    # 正則處理前，保留換行符，後續匹配跨行內容
    normalized_text = extracted_text

    # 定義正則表達式來提取內容
    dispatch_number_pattern = r"發文字號：([^\n]+)"
    serial_number_pattern = r"(1I\d{10,11})"
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"  # 精確匹配剛好 8 位的數字，且後面不能接 @
    subject_pattern = r"主旨：(.*?。)"  # 提取主旨內容，支持跨行，直到句點

    # 提取內容
    dispatch_number_match = re.search(dispatch_number_pattern, extracted_text)
    serial_number_match = re.search(serial_number_pattern, extracted_text)
    original_match = re.search(original_pattern, normalized_text)
    unified_ids = re.findall(unified_id_pattern, normalized_text)
    subject_match = re.search(subject_pattern, normalized_text, re.DOTALL)
    
    filtered_unified_id = [
        num for num in unified_ids
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
        "備註": subject,
        "類別": "當鋪"
    }


# 定義函數：處理資料夾內的所有 PDF 並輸出到 Excel
def process_folder(folder_path, output_excel, config):
    # 搜索資料夾內的所有 PDF 文件
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]

    # 依檔名排序（不含路徑，只看檔案名稱）
    pdf_files.sort(key=lambda x: os.path.basename(x))


    
    extracted_data = []
    for pdf_file in pdf_files:

        first_text = pdf_to_text(pdf_file).replace(" ","").replace("\n", "")  
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
        elif "課後照顧服務中心" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 課後照顧服務中心")
            data = extract_after_school_info(pdf_file)    
        elif "托嬰中心" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 托嬰中心")
            data = extract_infant_center_info(pdf_file) 
        elif "護理之家" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 護理之家")
            data = extract_nursing_home_info(pdf_file) 
        elif "居家長照機構" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 居家長照機構")
            data = extract_longtern_care_info(pdf_file)  

        elif "正本：桃園市政府" in first_text and "北區國稅局" in first_text[:int(len(first_text)/1.5)]:
            print(f"▶ {os.path.basename(pdf_file)} → 自治條例行業")
            data = extract_concern_industry_info(pdf_file, config)   
     
        #elif "分公司" in first_text[:len(first_text)//2] and "公司、分公司" not in first_text and "數據通信分公司" not in first_text[-len(first_text)//2:] and "中華電信股份有限公司資訊技術分公司" not in first_text[-len(first_text)//2:]:
        elif "分公司" in first_text[:int(len(first_text)/1.5)] and "分公司" in first_text[:400]:
            print(f"▶ {os.path.basename(pdf_file)} → 分公司")
            data = extract_branch_info(pdf_file, config) 
        elif "貴商業" in first_text[:350]:
            print(f"▶ {os.path.basename(pdf_file)} → 商業")
            data = extract_business_info(pdf_file, config) 
        elif "貴公司" in first_text[:350]:
            print(f"▶ {os.path.basename(pdf_file)} → 公司")
            data = extract_company_info(pdf_file, config) 
        elif "府衛" in first_text[:350]:
            print(f"▶ {os.path.basename(pdf_file)} → 其他衛福機構")
            data = extract_other_health_info(pdf_file)
        elif "府社" in first_text[:350]:
            print(f"▶ {os.path.basename(pdf_file)} → 其他社福機構")
            data = extract_other_health_info(pdf_file)  
        elif "府觀" in first_text[:350]:
            print(f"▶ {os.path.basename(pdf_file)} → 觀傳事業機構")
            data = extract_hostel_info(pdf_file)
        elif "府警刑" in first_text:
            print(f"▶ {os.path.basename(pdf_file)} → 當鋪")
            data = extract_pawnshop_info(pdf_file)

        else:
            print(f"▶ {os.path.basename(pdf_file)} → 其他類別")
            data = extract_rest_doc_info(pdf_file, config)

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