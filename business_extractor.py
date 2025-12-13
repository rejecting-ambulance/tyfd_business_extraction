import os
import re
import fitz
import pandas as pd
import tkinter as tk
from tkinter import filedialog


def pdf_to_text(pdf_path):
    """將 PDF 轉換為文字"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for i, page in enumerate(doc):
        text = page.get_text("text")
        full_text += f"--- 第 {i + 1} 頁 ---\n{text}\n"
    return full_text


def load_exclude_set(exclude_path):
    """載入排除的統一編號集合"""
    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip()))
    except FileNotFoundError:
        return set()


def extract_common_fields(text):
    """提取共通欄位：發文字號、收文流水號、主旨"""
    patterns = {
        "dispatch_number": r"發文字號：([^\n]+)",
        "serial_number": r"(1I\d{10,11})",
        "subject": r"主旨：(.*?。)"
    }
    
    results = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL if key == "subject" else 0)
        results[key] = match.group(1).strip().replace("\n", "") if match else "未匹配"
    
    return results


def extract_unified_ids(text, exclude_set):
    """提取並過濾統一編號"""
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"
    unified_ids = re.findall(unified_id_pattern, text)
    
    filtered_ids = [
        num for num in unified_ids
        if not (re.fullmatch(r"\d{8}", num) and num in exclude_set)
    ]
    
    return ", ".join(sorted(set(filtered_ids))) if filtered_ids else "無"


def extract_original_field(text):
    """提取正本欄位"""
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    match = re.search(original_pattern, text)
    return match.group(1).strip() if match else "未匹配"


def create_base_result(pdf_path, common_fields, category, unified_id="無", name=None, address=None, remark=None):
    """建立基礎結果字典"""
    return {
        "檔名": os.path.basename(pdf_path),
        "收文流水號": common_fields["serial_number"],
        "發文字號": common_fields["dispatch_number"],
        "統一編號": unified_id,
        "場所名稱": name,
        "場所地址": address,
        "備註": remark or common_fields["subject"],
        "類別": category
    }


# ==================== 醫事機構 ====================
def extract_clinic_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"機構名稱[:：]\s*([^\s:：()（）]+)"
    code_pattern = r"機構代碼[:：]\s*([A-Za-z0-9]{10})"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    
    name_match = re.search(name_pattern, cleaned)
    code_match = re.search(code_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(1).strip() if name_match else None
    address = addr_match.group(1).strip() if addr_match else None
    code = code_match.group(1).strip() if code_match else "未匹配"
    
    remark = f"{common['subject']}\n機構代碼: {code}"
    
    return create_base_result(pdf_path, common, "醫事機構", name=name, address=address, remark=remark)


# ==================== 補習班 ====================
def extract_cram_school_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+補習班(?:[\u4e00-\u9fff\d\w]*分班)?"
    addr_pattern = r"(班址[\s\S]*?(桃園市[^\n,，]*))"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(0).strip() if name_match else None
    address = addr_match.group(2).strip() if addr_match else None
    
    return create_base_result(pdf_path, common, "補習班", name=name, address=address)


# ==================== 幼兒園 ====================
def extract_kindergarten_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+幼兒園(?:[\u4e00-\u9fff\d\w]*分班)?"
    addr_pattern = r"(?:園址|班址)[^桃]*(桃園市[^\n\)）。,，]*)"
    original_pattern = r"正本：([^\n]+)"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    original_match = re.search(original_pattern, text)
    
    name = name_match.group(0).strip() if name_match else None
    if name:
        name = f'桃園市{name}'
    
    original = original_match.group(1).strip() if original_match else "未匹配"
    if "幼兒園" in original:
        name = original
    
    address = addr_match.group(1).strip() if addr_match else None
    
    return create_base_result(pdf_path, common, "幼兒園", name=name, address=address)


# ==================== 課後照顧服務中心 ====================
def extract_after_school_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"桃園市[\u4e00-\u9fff\d\w]+課後照顧服務中心(?:[\u4e00-\u9fff\d\w]*分班)?"
    addr_pattern = r"(中心地址[\s\S]*?(桃園市[^\n,，。]*))"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(0).strip() if name_match else None
    address = addr_match.group(2).strip() if addr_match else None
    
    return create_base_result(pdf_path, common, "課後照顧服務中心", name=name, address=address)


# ==================== 托嬰中心 ====================
def extract_infant_center_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"私立[\u4e00-\u9fff\d\w]+托嬰中心?"
    addr_pattern = r"(?:地址)[:：]桃*?(桃園市[^\n\)）。,，]*)"
    original_pattern = r"正本：([^\n]+)"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    original_match = re.search(original_pattern, text)
    
    name = name_match.group(0).strip() if name_match else None
    if name:
        name = f'桃園市{name}'
    
    original = original_match.group(1).strip() if original_match else "未匹配"
    if "托嬰中心" in original:
        name = original
    
    address = addr_match.group(1).strip() if addr_match else None
    
    return create_base_result(pdf_path, common, "托嬰中心", name=name, address=address)


# ==================== 護理之家 ====================
def extract_nursing_home_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(1).strip() if name_match else None
    address = addr_match.group(1).strip() if addr_match else None
    
    return create_base_result(pdf_path, common, "護理之家", name=name, address=address)


# ==================== 長照機構 ====================
def extract_longterm_care_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"機構名稱[:：]\s*([^\s:：()（）。]+)"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(1).strip() if name_match else None
    address = addr_match.group(1).strip().rstrip("。") if addr_match else "未匹配"
    
    return create_base_result(pdf_path, common, "長照機構", name=name, address=address)


# ==================== 自治條例行業 ====================
def extract_concern_industry_info(pdf_path, config):
    text = pdf_to_text(pdf_path)
    normalized = text.replace("\r", "").replace("\n", "").replace(" ", "")
    common = extract_common_fields(text)
    exclude_set = load_exclude_set(config.get("exclude_path", "exclude_numbers.txt"))
    
    # 提取名稱
    name_pattern = r"國稅局函准(.+?)統一"
    name_match = re.search(name_pattern, normalized)
    if name_match:
        name = name_match.group(1).strip()
        if name.endswith("（"):
            name = name[:-1].strip()
    else:
        name = "未匹配"
    
    # 提取統一編號
    unified_id_pattern = r"統一編號[:：](\d+)[。,]"
    unified_id_match = re.search(unified_id_pattern, normalized)
    unified_id = unified_id_match.group(1).strip() if unified_id_match else "未匹配"
    
    # 提取地址
    address_pattern = r"公司地址[:：]([^\)）]+)[\)）]"
    address_match = re.search(address_pattern, normalized)
    address = address_match.group(1).strip() if address_match else "未匹配"
    
    return create_base_result(pdf_path, common, "自治條例行業(資訊休閒、治安顧慮等)", 
                            unified_id=unified_id, name=name, address=address)


# ==================== 分公司 ====================
def extract_branch_info(pdf_path, config):
    text = pdf_to_text(pdf_path)
    normalized = text.replace("\r", "").replace("\n", "").replace(" ", "")
    common = extract_common_fields(text)
    exclude_set = load_exclude_set(config.get("exclude_path", "exclude_numbers.txt"))
    
    branch_pattern = r"申請(?:.*?所屬|在)?([\s\S]*?分公司)"
    original_pattern = r"正本：.*?([\u4e00-\u9fff\d\w]+公司)"
    addr_pattern = r"(?:分公司所在地|分公司地址|新地址)[^桃]*(桃園市[^\n\)）。,，;；]*)(?:[\)）。,，;；]|$)"
    
    branch_match = re.search(branch_pattern, normalized)
    original_match = re.search(original_pattern, normalized)
    addr_matches = re.findall(addr_pattern, normalized)
    
    branch_name = branch_match.group(1).strip() if branch_match else "未匹配"
    original = original_match.group(1).strip() if original_match else "未匹配"
    
    if addr_matches:
        address = addr_matches[1].strip() if len(addr_matches) >= 2 else addr_matches[0].strip()
        if "（" in address:
            address = f'{address}）'
        elif "(" in address:
            address = f'{address})'
    else:
        address = "未匹配"
    
    unified_id = extract_unified_ids(normalized, exclude_set)
    name = f"{original}{branch_name}"
    
    return create_base_result(pdf_path, common, "分公司", unified_id=unified_id, name=name, address=address)


# ==================== 商業 ====================
def extract_business_info(pdf_path, config):
    text = pdf_to_text(pdf_path)
    normalized = text.replace("\r", "").replace("\n", "").replace(" ", "")
    common = extract_common_fields(text)
    exclude_set = load_exclude_set(config.get("exclude_path", "exclude_numbers.txt"))
    
    original = extract_original_field(normalized)
    unified_id = extract_unified_ids(normalized, exclude_set)
    
    pattern = r"^(?P<name>[^\[（\(]+).*?\[\s*(?P<addr>[^\]]+)\s*\]"
    m = re.search(pattern, original)
    
    name = m.group("name").strip() if m else "未匹配"
    address = m.group("addr").strip() if m else "未匹配"
    
    return create_base_result(pdf_path, common, "商業", unified_id=unified_id, name=name, address=address)


# ==================== 公司 ====================
def extract_company_info(pdf_path, config):
    text = pdf_to_text(pdf_path)
    normalized = text.replace("\r", "").replace("\n", "").replace(" ", "")
    common = extract_common_fields(text)
    exclude_set = load_exclude_set(config.get("exclude_path", "exclude_numbers.txt"))
    
    original_pattern = r"正本：.*?([\u4e00-\u9fff\d\w]+公司)"
    addr_pattern = r"(?:公司所在地|公司地址|新地址|所在地為)[^桃]*(桃園市[^\n。,，;；]*)(?:[。,，;；]|$)"
    
    original_match = re.search(original_pattern, normalized)
    addr_match = re.search(addr_pattern, normalized)
    
    original = original_match.group(1).strip() if original_match else "未匹配"
    address = addr_match.group(1).strip() if addr_match else "未匹配"
    
    # 移除代理人部分
    match = re.search(r"(.+?)代理人：", original)
    if match:
        original = match.group(1).strip()
    
    unified_id = extract_unified_ids(normalized, exclude_set)
    
    return create_base_result(pdf_path, common, "公司", unified_id=unified_id, name=original, address=address)


# ==================== 其他衛福機構 ====================
def extract_other_health_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
    
    name_match = re.search(name_pattern, cleaned)
    addr_match = re.search(addr_pattern, cleaned)
    
    name = name_match.group(1).strip() if name_match else "未匹配"
    address = addr_match.group(1).strip() if addr_match else "未匹配"
    
    if name.endswith("。"):
        name = name[:-1]
    if address.endswith("。"):
        address = address[:-1]
    
    category = "其他衛福機構" if "府衛" in text[:350] else "其他社福機構"
    
    return create_base_result(pdf_path, common, category, name=name, address=address)


# ==================== 觀傳事業機構 ====================
def extract_hostel_info(pdf_path):
    text = pdf_to_text(pdf_path)
    cleaned = text.replace("\n", "").replace("\r", "")
    common = extract_common_fields(text)
    
    addr_pattern = r"地址[:：]\s*([^\s:：()（）。]+)"
    original_pattern = r"正本：([\s\S]*?)(?=副本)"
    
    addr_matches = re.findall(addr_pattern, cleaned)
    original_match = re.search(original_pattern, cleaned)
    
    address = addr_matches[-1].strip() if addr_matches else "未匹配"
    original = original_match.group(1).strip() if original_match else "未匹配"
    
    return create_base_result(pdf_path, common, "觀傳事業機構", name=original, address=address)


# ==================== 當舖 ====================
def extract_pawnshop_info(pdf_path):
    text = pdf_to_text(pdf_path)
    common = extract_common_fields(text)
    
    original = extract_original_field(text)
    unified_id_pattern = r"(?<!\d)(\d{8})(?!\d)"
    unified_ids = re.findall(unified_id_pattern, text)
    unified_id = ", ".join(sorted(set(unified_ids))) if unified_ids else "無"
    
    return create_base_result(pdf_path, common, "當舖", unified_id=unified_id, name=original, address="桃園市")


# ==================== 其他類別 ====================
def extract_rest_doc_info(pdf_path, config):
    text = pdf_to_text(pdf_path)
    common = extract_common_fields(text)
    exclude_set = load_exclude_set(config.get("exclude_path", "exclude_numbers.txt"))
    
    original = extract_original_field(text)
    unified_id = extract_unified_ids(text, exclude_set)
    
    return create_base_result(pdf_path, common, "其他類別", unified_id=unified_id, name=original, address="桃園市")


# ==================== 主處理函數 ====================
def process_folder(folder_path, output_excel, config):
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]
    pdf_files.sort(key=lambda x: os.path.basename(x))
    
    extracted_data = []
    
    for pdf_file in pdf_files:
        first_text = pdf_to_text(pdf_file).replace(" ", "").replace("\n", "")
        filename = os.path.basename(pdf_file)
        
        # 路由邏輯
        if "機構代碼" in first_text:
            print(f"▶ {filename} → 醫事機構")
            data = extract_clinic_info(pdf_file)
        elif "補習班" in first_text:
            print(f"▶ {filename} → 補習班")
            data = extract_cram_school_info(pdf_file)
        elif "幼兒園" in first_text:
            print(f"▶ {filename} → 幼兒園")
            data = extract_kindergarten_info(pdf_file)
        elif "課後照顧服務中心" in first_text:
            print(f"▶ {filename} → 課後照顧服務中心")
            data = extract_after_school_info(pdf_file)
        elif "托嬰中心" in first_text:
            print(f"▶ {filename} → 托嬰中心")
            data = extract_infant_center_info(pdf_file)
        elif "護理之家" in first_text:
            print(f"▶ {filename} → 護理之家")
            data = extract_nursing_home_info(pdf_file)
        elif "居家長照機構" in first_text:
            print(f"▶ {filename} → 居家長照機構")
            data = extract_longterm_care_info(pdf_file)
        elif "正本：桃園市政府" in first_text and "北區國稅局" in first_text[:int(len(first_text)/1.5)]:
            print(f"▶ {filename} → 自治條例行業")
            data = extract_concern_industry_info(pdf_file, config)
        elif "分公司" in first_text[:int(len(first_text)/1.5)] and "分公司" in first_text[:400]:
            print(f"▶ {filename} → 分公司")
            data = extract_branch_info(pdf_file, config)
        elif "貴商業" in first_text[:350]:
            print(f"▶ {filename} → 商業")
            data = extract_business_info(pdf_file, config)
        elif "貴公司" in first_text[:350]:
            print(f"▶ {filename} → 公司")
            data = extract_company_info(pdf_file, config)
        elif "府衛" in first_text[:350]:
            print(f"▶ {filename} → 其他衛福機構")
            data = extract_other_health_info(pdf_file)
        elif "府社" in first_text[:350]:
            print(f"▶ {filename} → 其他社福機構")
            data = extract_other_health_info(pdf_file)
        elif "府觀" in first_text[:350]:
            print(f"▶ {filename} → 觀傳事業機構")
            data = extract_hostel_info(pdf_file)
        elif "府警刑" in first_text:
            print(f"▶ {filename} → 當舖")
            data = extract_pawnshop_info(pdf_file)
        else:
            print(f"▶ {filename} → 其他類別")
            data = extract_rest_doc_info(pdf_file, config)
        
        extracted_data.append(data)
    
    # 建立 DataFrame 並匯出
    df = pd.DataFrame(extracted_data)
    df.insert(0, "編號", range(1, len(df) + 1))
    df.to_excel(output_excel, index=False)
    
    print(f"提取結果已保存至：{output_excel}")
    os.startfile(output_excel)


def select_folder_gui():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="選取 PDF 所在的資料夾")
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
