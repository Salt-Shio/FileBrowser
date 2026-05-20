"""
手動重置與清理上傳會話與測試資料腳本 (Manual Cleanup & Restore Script)
職責：
1. 清空 SQLite 資料庫中所有的活躍/過期分塊上傳會話 (upload_sessions)。
2. 清理 DB 中所有生成的測試檔案與資料夾記錄 (ID 以 test-gc- 開頭)。
3. 實體刪除磁碟上所有臨時產生的暫存碎片資料夾 (/data/temp/*)。
4. 實體刪除磁碟上產生的上傳測試檔案 (/data/uploads/test-file-*)。
5. 使用相對路徑動態推算專案根目錄，徹底免除 Windows 個人硬編碼路徑限制。
"""
import sqlite3
import os
import shutil
import sys
import io

# 確保 Windows 主機端的 stdout 支援 UTF-8 編碼以防止 Emoji 造成 CP950 崩潰
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def main():
    # 1. 基於本腳本的實實位置，動態推算專案根目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    db_path = os.path.join(project_root, "db", "file_explorer.db")
    temp_dir = os.path.join(project_root, "data", "temp")
    uploads_dir = os.path.join(project_root, "data", "uploads")
    
    print("=" * 60)
    print("🧹 正在執行 VFS 垃圾與測試資料清理大掃除...")
    print(f"📌 動態定位資料庫路徑: {db_path}")
    print(f"📌 動態定位暫存目錄路徑: {temp_dir}")
    print(f"📌 動態定位上傳目錄路徑: {uploads_dir}")
    print("=" * 60)

    # 2. 清理資料庫會話與測試資料
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            # 強制啟用 WAL 模式，測試是否能防止日誌抹除
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            
            # 清除所有上傳會話 (包括非測試產生的以防殘留，或僅清除 test-gc-)
            cursor.execute("DELETE FROM upload_sessions")
            deleted_sessions = cursor.rowcount
            
            # 清除測試檔案
            cursor.execute("DELETE FROM files WHERE id LIKE 'test-gc-%'")
            deleted_files = cursor.rowcount
            
            # 清除測試目錄
            cursor.execute("DELETE FROM folders WHERE id LIKE 'test-gc-%'")
            deleted_folders = cursor.rowcount
            
            conn.commit()
            conn.close()
            print(f"✅ 成功清除資料庫中的 {deleted_sessions} 個上傳會話記錄！")
            print(f"✅ 成功清除資料庫中的 {deleted_files} 筆測試檔案記錄！")
            print(f"✅ 成功清除資料庫中的 {deleted_folders} 筆測試目錄記錄！")
        except Exception as e:
            print(f"❌ 清理資料庫失敗: {e}")
    else:
        print("⚠️ 找不到資料庫檔案，跳過 DB 清理。")

    # 3. 清理實體磁碟暫存碎片 (/data/temp/*)
    if os.path.exists(temp_dir):
        try:
            count = 0
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    count += 1
            print(f"✅ 成功物理清除磁碟中的 {count} 個暫存分塊碎片資料夾！")
        except Exception as e:
            print(f"❌ 物理磁碟暫存清理失敗: {e}")
    else:
        print("⚠️ 找不到實體暫存目錄，跳過暫存磁碟清理。")
        
    # 4. 清理實體磁碟上傳測試檔 (/data/uploads/test-file-*)
    if os.path.exists(uploads_dir):
        try:
            count = 0
            for item in os.listdir(uploads_dir):
                if item.startswith("test-file-"):
                    item_path = os.path.join(uploads_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        count += 1
            print(f"✅ 成功物理清除磁碟中的 {count} 個測試正式上傳檔案！")
        except Exception as e:
            print(f"❌ 物理磁碟上傳清理失敗: {e}")
    else:
        print("⚠️ 找不到實體上傳目錄，跳過上傳磁碟清理。")
        
    print("=" * 60)
    print("🎉 垃圾回收大掃除與測試環境還原完成！")
    print("=" * 60)

    # 輸出 3 次強烈警告以防開發人員遺漏重啟
    for i in range(3):
        print(f"\n⚠️ ⚠️ ⚠️  【 重 要 警 告 ({i+1}/3) 】 ⚠️ ⚠️ ⚠️")
        print("    [問題] 此腳本在本機 Windows 執行時，會強行抹除 Docker 內的 SQLite WAL 與 SHM 臨時日誌檔。")
        print("    [後果] 若不立刻重啟容器，後續在網頁上的任何資料庫寫入（例如：啟用 2FA、上傳檔案）均會無聲蒸發或報錯！")
        print("    [操作] 請立即執行指令：docker-compose restart server")
        print("⚠️ " * 35)
    print()

if __name__ == "__main__":
    main()
