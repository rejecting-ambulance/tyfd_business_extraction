import os
import shutil
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox

# 第三方套件
# pip install rarfile py7zr
import rarfile
import py7zr

SUPPORTED_EXTS = ('.zip', '.rar', '.7z')


def extract_archive(archive_path, target_dir):
    """依副檔名解壓縮"""
    if archive_path.lower().endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            z.extractall(target_dir)
    elif archive_path.lower().endswith('.rar'):
        with rarfile.RarFile(archive_path) as r:
            r.extractall(target_dir)
    elif archive_path.lower().endswith('.7z'):
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            z.extractall(target_dir)


def start_process(folder):
    log_text.delete('1.0', tk.END)
    log('開始處理資料夾：' + folder)

    if not folder:
        messagebox.showerror('錯誤', '請選擇資料夾')
        return

    compressed_dir = os.path.join(folder, '壓縮檔')
    merged_dir = os.path.join(folder, '合併後檔案')

    os.makedirs(compressed_dir, exist_ok=True)
    os.makedirs(merged_dir, exist_ok=True)

    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path) and file.lower().endswith(SUPPORTED_EXTS):
            temp_extract_dir = os.path.join(folder, '__temp_extract__')
            os.makedirs(temp_extract_dir, exist_ok=True)

            try:
                log(f'解壓縮中：{file}')
                extract_archive(file_path, temp_extract_dir)
            except Exception as e:
                messagebox.showwarning('解壓失敗', f'{file}\n{e}')
                continue

            # 合併所有解壓後的檔案
            for root, _, files in os.walk(temp_extract_dir):
                for f in files:
                    src = os.path.join(root, f)
                    dst = os.path.join(merged_dir, f)

                    # 避免檔名衝突
                    base, ext = os.path.splitext(f)
                    counter = 1
                    while os.path.exists(dst):
                        dst = os.path.join(merged_dir, f"{base}_{counter}{ext}")
                        counter += 1

                    log(f'  合併檔案：{os.path.basename(dst)}')
                    shutil.move(src, dst)

            shutil.rmtree(temp_extract_dir)
            log(f'  移動壓縮檔至【壓縮檔】：{file}')
            shutil.move(file_path, os.path.join(compressed_dir, file))

    log('處理完成')
    messagebox.showinfo('完成', '所有壓縮檔已解壓並合併完成')


# ===== GUI =====
root = tk.Tk()
root.title('批次解壓縮合併工具')
root.geometry('600x420')

folder_var = tk.StringVar()

# ===== Log Area =====
def log(msg):
    log_text.insert(tk.END, msg + '\n')
    log_text.see(tk.END)



def browse():
    folder = filedialog.askdirectory()
    folder_var.set(folder)


tk.Label(root, text='選擇要處理的資料夾').pack(pady=10)

frame = tk.Frame(root)
frame.pack()

tk.Entry(frame, textvariable=folder_var, width=40).pack(side='left', padx=5)
tk.Button(frame, text='瀏覽', command=browse).pack(side='left')

tk.Button(root, text='開始處理', command=lambda: start_process(folder_var.get()), height=2).pack(pady=10)

log_text = tk.Text(root, height=15, width=70)
log_text.pack(pady=5)

root.mainloop()
