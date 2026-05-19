"""
手動重置與清理上傳會話腳本 (Manual Cleanup Script)
職責：
1. 清空 SQLite 資料庫中所有的活躍/過期分塊上傳會話 (upload_sessions)。
2. 實體刪除磁碟上所有臨時產生的暫存碎片資料夾 (/data/temp/*)。
3. 使用相對路徑動態推算專案根目錄，徹底免除 Windows 個人硬編碼路徑限制。
"""
import sqlite3
import os
import shutil

def main():
    # 1. 基於本腳本的實實位置，動態推算專案根目錄
    # 腳本路徑為：server/scripts/clean_sessions.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    db_path = os.path.join(project_root, "db", "file_explorer.db")
    temp_dir = os.path.join(project_root, "data", "temp")
    
    print("=" * 60)
    print("🧹 正在執行 VFS 垃圾清理大掃除...")
    print(f"📌 動態定位資料庫路徑: {db_path}")
    print(f"📌 動態定位暫存目錄路徑: {temp_dir}")
    print("=" * 60)

    # 2. 清理資料庫會話
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.conn.cursor() if hasattr(conn, "conn") else conn.cursor()
            cursor.execute("DELETE FROM upload_sessions")
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            print(f"✅ 成功清除資料庫中的 {deleted} 個活躍/過期上傳會話記錄！")
        except Exception as e:
            print(f"❌ 清理資料庫失敗: {e}")
    else:
        print("⚠️ 找不到資料庫檔案，跳過 DB 清理。")

    # 3. 清理實體磁碟暫存碎片
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
            print(f"❌ 物理磁碟清理失敗: {e}")
    else:
        print("⚠️ 找不到實體暫存目錄，跳過磁碟清理。")
        
    print("=" * 60)
    print("🎉 垃圾回收大掃除手動重置完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
