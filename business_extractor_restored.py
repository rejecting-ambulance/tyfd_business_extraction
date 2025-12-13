import os
import re
import fitz
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from dataclasses import dataclass
from typing import Optional, Dict, Callable, Set
from pathlib import Path


@dataclass
class ExtractionResult:
    """資料提取結果"""
    filename: str
    serial_number: str
    dispatch_number: str
    unified_id: str
    location_name: Optional[str]
    location_address: Optional[str]
    remark: str
    category: str
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "檔名": self.filename,
            "收文流水號": self.serial_number,
            "發文字號": self.dispatch_number,
            "統一編號": self.unified_id,
            "場所名稱": self.location_name,
            "場所地址": self.location_address,
            "備註": self.remark,
            "類別": self.category
        }


class PDFTextExtractor:
    """PDF 文字提取器"""
    
    @staticmethod
    def extract(pdf_path: str) -> str:
        """提取 PDF 全文"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for i, page in enumerate(doc):
                text = page.get_text("text")
                full_text += f"--- 第 {i + 1} 頁 ---\n{text}\n"
            doc.close()
            return full_text
        except Exception as e:
            print(f"⚠️  讀取 PDF 失敗 ({pdf_path}): {e}")
            return ""
    
    @staticmethod
    def clean_text(text: str, remove_newlines: bool = False) -> str:
        """清理文字"""
        if remove_newlines:
            return text.replace("\n", "").replace("\r", "").replace(" ", "")
        return text


class CommonFieldExtractor:
    """共通欄位提取器"""
    
    PATTERNS = {
        "dispatch_number": r"發文字號：([^\n]+)",
        "serial_number": r"(1I\d{10,11})",
        "subject": r"主旨：(.*?。)",
        "original": r"正本：([\s\S]*?)(?=副本)"
    }
    
    @classmethod
    def extract(cls, text: str) -> Dict[str, str]:
        """提取共通欄位"""
        results = {}
        for key, pattern in cls.PATTERNS.items():
            flags = re.DOTALL if key in ["subject", "original"] else 0
            match = re.search(pattern, text, flags)
            if match:
                value = match.group(1).strip()
                if key == "subject":
                    value = value.replace("\n", "")
                results[key] = value
            else:
                results[key] = "未匹配"
        return results
    
    @staticmethod
    def extract_unified_ids(text: str, exclude_set: Set[str]) -> str:
        """提取並過濾統一編號"""
        pattern = r"(?<!\d)(\d{8})(?!\d)"
        unified_ids = re.findall(pattern, text)
        filtered = [uid for uid in unified_ids if uid not in exclude_set]
        return ", ".join(sorted(set(filtered))) if filtered else "無"


class DocumentClassifier:
    """文件類型分類器"""
    
    RULES = [
        ("機構代碼", "醫事機構"),
        ("補習班", "補習班"),
        ("幼兒園", "幼兒園"),
        ("課後照顧服務中心", "課後照顧服務中心"),
        ("托嬰中心", "托嬰中心"),
        ("護理之家", "護理之家"),
        ("居家長照機構", "長照機構"),
    ]
    
    @classmethod
    def classify(cls, text: str) -> Optional[str]:
        """根據文字內容分類文件類型"""
        text_length = len(text)
        
        # 簡單規則匹配
        for keyword, category in cls.RULES:
            if keyword in text:
                return category
        
        # 複雜規則
        if "正本：桃園市政府" in text and "北區國稅局" in text[:int(text_length/1.5)]:
            return "自治條例行業"
        
        if "分公司" in text[:int(text_length/1.5)] and "分公司" in text[:400]:
            return "分公司"
        
        if "貴商業" in text[:350]:
            return "商業"
        
        if "貴公司" in text[:350]:
            return "公司"
        
        if "府衛" in text[:350]:
            return "其他衛福機構"
        
        if "府社" in text[:350]:
            return "其他社福機構"
        
        if "府觀" in text[:350]:
            return "觀傳事業機構"
        
        if "府警刑" in text:
            return "當舖"
        
        return "其他類別"


class BaseExtractor:
    """基礎提取器"""
    
    def __init__(self, pdf_path: str, config: Dict = None):
        self.pdf_path = pdf_path
        self.config = config or {}
        self.raw_text = PDFTextExtractor.extract(pdf_path)
        self.cleaned_text = PDFTextExtractor.clean_text(self.raw_text, remove_newlines=True)
        self.common_fields = CommonFieldExtractor.extract(self.raw_text)
        self.exclude_set = self._load_exclude_set()
    
    def _load_exclude_set(self) -> Set[str]:
        """載入排除集合"""
        exclude_path = self.config.get("exclude_path", "exclude_numbers.txt")
        try:
            with open(exclude_path, "r", encoding="utf-8") as f:
                return {line.strip() for line in f if re.fullmatch(r"\d{8}", line.strip())}
        except FileNotFoundError:
            return set()
    
    def create_result(self, category: str, unified_id: str = "無", 
                     name: Optional[str] = None, address: Optional[str] = None, 
                     remark: Optional[str] = None) -> ExtractionResult:
        """建立提取結果"""
        return ExtractionResult(
            filename=Path(self.pdf_path).name,
            serial_number=self.common_fields["serial_number"],
            dispatch_number=self.common_fields["dispatch_number"],
            unified_id=unified_id,
            location_name=name,
            location_address=address,
            remark=remark or self.common_fields["subject"],
            category=category
        )
    
    def extract(self) -> ExtractionResult:
        """提取資料 - 子類別需實作"""
        raise NotImplementedError


class ClinicExtractor(BaseExtractor):
    """醫事機構提取器"""
    
    def extract(self) -> ExtractionResult:
        patterns = {
            "name": r"機構名稱[:：]\s*([^\s:：()（）]+)",
            "code": r"機構代碼[:：]\s*([A-Za-z0-9]{10})",
            "address": r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
        }
        
        matches = {k: re.search(v, self.cleaned_text) for k, v in patterns.items()}
        
        name = matches["name"].group(1).strip() if matches["name"] else None
        code = matches["code"].group(1).strip() if matches["code"] else "未匹配"
        address = matches["address"].group(1).strip() if matches["address"] else None
        
        remark = f"{self.common_fields['subject']}\n機構代碼: {code}"
        
        return self.create_result("醫事機構", name=name, address=address, remark=remark)


class CramSchoolExtractor(BaseExtractor):
    """補習班提取器"""
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"私立[\u4e00-\u9fff\d\w]+補習班(?:[\u4e00-\u9fff\d\w]*分班)?"
        addr_pattern = r"(班址[\s\S]*?(桃園市[^\n,，]*))"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(0).strip() if name_match else None
        address = addr_match.group(2).strip() if addr_match else None
        
        return self.create_result("補習班", name=name, address=address)


class KindergartenExtractor(BaseExtractor):
    """幼兒園提取器"""
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"私立[\u4e00-\u9fff\d\w]+幼兒園(?:[\u4e00-\u9fff\d\w]*分班)?"
        addr_pattern = r"(?:園址|班址)[^桃]*(桃園市[^\n\)）。,，]*)"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(0).strip() if name_match else None
        if name:
            name = f'桃園市{name}'
        
        # 檢查正本欄位
        if "幼兒園" in self.common_fields["original"]:
            name = self.common_fields["original"]
        
        address = addr_match.group(1).strip() if addr_match else None
        
        return self.create_result("幼兒園", name=name, address=address)


class AfterSchoolExtractor(BaseExtractor):
    """課後照顧服務中心提取器"""
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"桃園市[\u4e00-\u9fff\d\w]+課後照顧服務中心(?:[\u4e00-\u9fff\d\w]*分班)?"
        addr_pattern = r"(中心地址[\s\S]*?(桃園市[^\n,，。]*))"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(0).strip() if name_match else None
        address = addr_match.group(2).strip() if addr_match else None
        
        return self.create_result("課後照顧服務中心", name=name, address=address)


class InfantCenterExtractor(BaseExtractor):
    """托嬰中心提取器"""
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"私立[\u4e00-\u9fff\d\w]+托嬰中心?"
        addr_pattern = r"(?:地址)[:：]桃*?(桃園市[^\n\)）。,，]*)"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(0).strip() if name_match else None
        if name:
            name = f'桃園市{name}'
        
        if "托嬰中心" in self.common_fields["original"]:
            name = self.common_fields["original"]
        
        address = addr_match.group(1).strip() if addr_match else None
        
        return self.create_result("托嬰中心", name=name, address=address)


class InstitutionExtractor(BaseExtractor):
    """機構類提取器（護理之家、長照機構等）"""
    
    def __init__(self, pdf_path: str, category: str, config: Dict = None):
        super().__init__(pdf_path, config)
        self.category = category
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
        addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(1).strip() if name_match else None
        address = addr_match.group(1).strip().rstrip("。") if addr_match else "未匹配"
        
        return self.create_result(self.category, name=name, address=address)


class BusinessExtractor(BaseExtractor):
    """商業/公司提取器基類"""
    
    def get_unified_ids(self) -> str:
        """取得統一編號"""
        return CommonFieldExtractor.extract_unified_ids(self.cleaned_text, self.exclude_set)


class ConcernIndustryExtractor(BusinessExtractor):
    """自治條例行業提取器"""
    
    def extract(self) -> ExtractionResult:
        # 提取名稱
        name_pattern = r"國稅局函准(.+?)統一"
        name_match = re.search(name_pattern, self.cleaned_text)
        name = "未匹配"
        if name_match:
            name = name_match.group(1).strip().rstrip("（")
        
        # 提取統一編號
        unified_pattern = r"統一編號[:：](\d+)[。,]"
        unified_match = re.search(unified_pattern, self.cleaned_text)
        unified_id = unified_match.group(1).strip() if unified_match else "未匹配"
        
        # 提取地址
        addr_pattern = r"公司地址[:：]([^\)）]+)[\)）]"
        addr_match = re.search(addr_pattern, self.cleaned_text)
        address = addr_match.group(1).strip() if addr_match else "未匹配"
        
        return self.create_result("自治條例行業(資訊休閒、治安顧慮等)", 
                                unified_id=unified_id, name=name, address=address)


class BranchExtractor(BusinessExtractor):
    """分公司提取器"""
    
    def extract(self) -> ExtractionResult:
        branch_pattern = r"申請(?:.*?所屬|在)?([\s\S]*?分公司)"
        branch_match = re.search(branch_pattern, self.cleaned_text)
        branch_name = branch_match.group(1).strip() if branch_match else "未匹配"
        
        original = self.common_fields["original"]
        company_pattern = r"([\u4e00-\u9fff\d\w]+公司)"
        company_match = re.search(company_pattern, original)
        company_name = company_match.group(1).strip() if company_match else "未匹配"
        
        # 提取地址
        addr_pattern = r"(?:分公司所在地|分公司地址|新地址)[^桃]*(桃園市[^\n\)）。,，;；]*)(?:[\)）。,，;；]|$)"
        addr_matches = re.findall(addr_pattern, self.cleaned_text)
        
        address = "未匹配"
        if addr_matches:
            address = addr_matches[1].strip() if len(addr_matches) >= 2 else addr_matches[0].strip()
            if "（" in address:
                address = f'{address}）'
            elif "(" in address:
                address = f'{address})'
        
        name = f"{company_name}{branch_name}"
        unified_id = self.get_unified_ids()
        
        return self.create_result("分公司", unified_id=unified_id, name=name, address=address)


class CommercialExtractor(BusinessExtractor):
    """商業提取器"""
    
    def extract(self) -> ExtractionResult:
        original = self.common_fields["original"]
        pattern = r"^(?P<name>[^\[（\(]+).*?\[\s*(?P<addr>[^\]]+)\s*\]"
        match = re.search(pattern, original)
        
        name = match.group("name").strip() if match else "未匹配"
        address = match.group("addr").strip() if match else "未匹配"
        unified_id = self.get_unified_ids()
        
        return self.create_result("商業", unified_id=unified_id, name=name, address=address)


class CompanyExtractor(BusinessExtractor):
    """公司提取器"""
    
    def extract(self) -> ExtractionResult:
        company_pattern = r"([\u4e00-\u9fff\d\w]+公司)"
        company_match = re.search(company_pattern, self.common_fields["original"])
        name = company_match.group(1).strip() if company_match else "未匹配"
        
        # 移除代理人部分
        agent_match = re.search(r"(.+?)代理人：", name)
        if agent_match:
            name = agent_match.group(1).strip()
        
        # 提取地址
        addr_pattern = r"(?:公司所在地|公司地址|新地址|所在地為)[^桃]*(桃園市[^\n。,，;；]*)(?:[。,，;；]|$)"
        addr_match = re.search(addr_pattern, self.cleaned_text)
        address = addr_match.group(1).strip() if addr_match else "未匹配"
        
        unified_id = self.get_unified_ids()
        
        return self.create_result("公司", unified_id=unified_id, name=name, address=address)


class OtherHealthExtractor(BaseExtractor):
    """其他衛福機構提取器"""
    
    def __init__(self, pdf_path: str, category: str, config: Dict = None):
        super().__init__(pdf_path, config)
        self.category = category
    
    def extract(self) -> ExtractionResult:
        name_pattern = r"機構名稱[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
        addr_pattern = r"機構地址[:：]\s*([\s\S]*?)(?=\([一二三四五六七八九十百千]+\))"
        
        name_match = re.search(name_pattern, self.cleaned_text)
        addr_match = re.search(addr_pattern, self.cleaned_text)
        
        name = name_match.group(1).strip().rstrip("。") if name_match else "未匹配"
        address = addr_match.group(1).strip().rstrip("。") if addr_match else "未匹配"
        
        return self.create_result(self.category, name=name, address=address)


class HostelExtractor(BaseExtractor):
    """觀傳事業機構提取器"""
    
    def extract(self) -> ExtractionResult:
        addr_pattern = r"地址[:：]\s*([^\s:：()（）。]+)"
        addr_matches = re.findall(addr_pattern, self.cleaned_text)
        address = addr_matches[-1].strip() if addr_matches else "未匹配"
        
        name = self.common_fields["original"]
        
        return self.create_result("觀傳事業機構", name=name, address=address)


class PawnshopExtractor(BaseExtractor):
    """當舖提取器"""
    
    def extract(self) -> ExtractionResult:
        name = self.common_fields["original"]
        pattern = r"(?<!\d)(\d{8})(?!\d)"
        unified_ids = re.findall(pattern, self.raw_text)
        unified_id = ", ".join(sorted(set(unified_ids))) if unified_ids else "無"
        
        return self.create_result("當舖", unified_id=unified_id, name=name, address="桃園市")


class DefaultExtractor(BaseExtractor):
    """預設提取器（其他類別）"""
    
    def extract(self) -> ExtractionResult:
        name = self.common_fields["original"]
        unified_id = CommonFieldExtractor.extract_unified_ids(self.raw_text, self.exclude_set)
        
        return self.create_result("其他類別", unified_id=unified_id, name=name, address="桃園市")


class ExtractorFactory:
    """提取器工廠"""
    
    EXTRACTOR_MAP: Dict[str, type] = {
        "醫事機構": ClinicExtractor,
        "補習班": CramSchoolExtractor,
        "幼兒園": KindergartenExtractor,
        "課後照顧服務中心": AfterSchoolExtractor,
        "托嬰中心": InfantCenterExtractor,
        "護理之家": lambda p, c: InstitutionExtractor(p, "護理之家", c),
        "長照機構": lambda p, c: InstitutionExtractor(p, "長照機構", c),
        "自治條例行業": ConcernIndustryExtractor,
        "分公司": BranchExtractor,
        "商業": CommercialExtractor,
        "公司": CompanyExtractor,
        "其他衛福機構": lambda p, c: OtherHealthExtractor(p, "其他衛福機構", c),
        "其他社福機構": lambda p, c: OtherHealthExtractor(p, "其他社福機構", c),
        "觀傳事業機構": HostelExtractor,
        "當舖": PawnshopExtractor,
        "其他類別": DefaultExtractor
    }
    
    @classmethod
    def create(cls, category: str, pdf_path: str, config: Dict = None) -> BaseExtractor:
        """根據類別建立對應的提取器"""
        extractor_class = cls.EXTRACTOR_MAP.get(category, DefaultExtractor)
        return extractor_class(pdf_path, config)


class PDFProcessor:
    """PDF 批次處理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def process_folder(self, folder_path: str, output_excel: str):
        """處理資料夾中的所有 PDF"""
        pdf_files = sorted(
            [f for f in Path(folder_path).glob("*.pdf")],
            key=lambda x: x.name
        )
        
        if not pdf_files:
            print("❌ 資料夾中沒有 PDF 檔案")
            return
        
        print(f"📁 找到 {len(pdf_files)} 個 PDF 檔案\n")
        
        results = []
        for pdf_file in pdf_files:
            try:
                result = self._process_single_file(str(pdf_file))
                results.append(result.to_dict())
            except Exception as e:
                print(f"❌ 處理失敗: {pdf_file.name} - {e}")
        
        self._save_to_excel(results, output_excel)
    
    def _process_single_file(self, pdf_path: str) -> ExtractionResult:
        """處理單個 PDF 檔案"""
        filename = Path(pdf_path).name
        text = PDFTextExtractor.extract(pdf_path)
        cleaned_text = PDFTextExtractor.clean_text(text, remove_newlines=True)
        
        # 分類
        category = DocumentClassifier.classify(cleaned_text)
        print(f"▶ {filename} → {category}")
        
        # 提取
        extractor = ExtractorFactory.create(category, pdf_path, self.config)
        return extractor.extract()
    
    def _save_to_excel(self, results: list, output_path: str):
        """儲存為 Excel"""
        df = pd.DataFrame(results)
        df.insert(0, "編號", range(1, len(df) + 1))
        df.to_excel(output_path, index=False)
        
        print(f"\n✅ 提取結果已保存至：{output_path}")
        
        try:
            os.startfile(output_path)
        except Exception:
            pass


def select_folder_gui() -> Optional[str]:
    """GUI 選擇資料夾"""
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="選取 PDF 所在的資料夾")
    root.destroy()
    
    if not folder:
        print("❌ 未選取資料夾，程式中止。")
        return None
    
    return folder


def main():
    """主程式"""
    folder_path = select_folder_gui()
    if not folder_path:
        return
    
    output_excel = "business_extraction.xlsx"
    processor = PDFProcessor(config={})
    processor.process_folder(folder_path, output_excel)


if __name__ == "__main__":
    main()
