import pandas as pd
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

# =====================
# 主視窗
# =====================
root = tk.Tk()
root.title("PDF 批次重新命名與分類工具")
root.geometry("650x220")
root.resizable(False, False)

excel_path_var = tk.StringVar()
pdf_folder_var = tk.StringVar()

# =====================
# 選擇 Excel
# =====================
def select_excel():
    path = filedialog.askopenfilename(
        title="選擇 Excel 檔案",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if path:
        excel_path_var.set(path)

# =====================
# 選擇 PDF 資料夾
# =====================
def select_pdf_folder():
    path = filedialog.askdirectory(title="選擇 PDF 資料夾")
    if path:
        pdf_folder_var.set(path)

# =====================
# 執行主程式
# =====================
def execute():
    excel_path = excel_path_var.get()
    pdf_folder_path = pdf_folder_var.get()

    if not excel_path or not pdf_folder_path:
        messagebox.showerror("錯誤", "請先選擇 Excel 與 PDF 資料夾")
        return

    # 讀取 Excel
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        messagebox.showerror("Excel 讀取失敗", str(e))
        return

    current_col_name = "現有檔名"
    new_col_name = "新檔名"

    if current_col_name not in df.columns or new_col_name not in df.columns:
        messagebox.showerror(
            "欄位錯誤",
            f"Excel 必須包含欄位：{current_col_name}、{new_col_name}"
        )
        return

    df = df[[current_col_name, new_col_name]]
    df.columns = ["current_name", "new_name"]

    rename_count = 0
    rename_fail = 0

    for current_name, new_name in zip(df["current_name"], df["new_name"]):

        if current_name == "None" or current_name == 0:
            continue
        current_name_pdf = str(current_name).strip()
        new_name_pdf = f"{str(new_name).strip()}.pdf"

        current_path = os.path.join(pdf_folder_path, current_name_pdf)
        new_path = os.path.join(pdf_folder_path, new_name_pdf)

        # --- 檔案不存在，無法重新命名 ---
        if not os.path.exists(current_path):
            rename_fail += 1
            continue

        # --- 重新命名（只要這步成功就算成功） ---
        try:
            os.rename(current_path, new_path)
            rename_count += 1
        except Exception:
            rename_fail += 1
            continue

        # --- 分類移動（不影響統計） ---
        try:
            region = new_name.split("-")[-1].strip()
            region_folder = os.path.join(pdf_folder_path, region)
            os.makedirs(region_folder, exist_ok=True)
            shutil.move(new_path, os.path.join(region_folder, new_name_pdf))
        except Exception:
            pass  # 分類失敗不影響重新命名統計

    messagebox.showinfo(
        "完成",
        f"重新命名完成！\n"
        f"成功重新命名：{rename_count} 筆\n"
        f"失敗：{rename_fail} 筆"
    )
    

# =====================
# 版面配置
# =====================
tk.Label(root, text="Excel 檔案：").place(x=20, y=30)
tk.Entry(root, textvariable=excel_path_var, width=65).place(x=100, y=30)
tk.Button(root, text="選擇", command=select_excel).place(x=560, y=26)

tk.Label(root, text="檔案資料夾：").place(x=20, y=80)
tk.Entry(root, textvariable=pdf_folder_var, width=65).place(x=100, y=80)
tk.Button(root, text="選擇", command=select_pdf_folder).place(x=560, y=76)

tk.Button(
    root,
    text="開始執行",
    width=20,
    height=2,
    command=execute,
    bg="#4CAF50",
    fg="white"
).place(x=240, y=140)

root.mainloop()
