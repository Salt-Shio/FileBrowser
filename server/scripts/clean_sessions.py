import sqlite3
import os
import shutil

def main():
    db_path = r"c:\Users\salt\Desktop\Project\FileBrowser\db\file_explorer.db"
    
    # 1. 清理資料庫會話
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM upload_sessions")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Cleaned {deleted} active upload sessions in database successfully!")
    else:
        print("Database file not found.")

    # 2. 清理實體磁碟暫存碎片
    temp_dir = r"c:\Users\salt\Desktop\Project\FileBrowser\data\temp"
    if os.path.exists(temp_dir):
        # 刪除 temp 目錄下的子資料夾 (每個 upload_id 對應的目錄)
        count = 0
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                count += 1
        print(f"Cleaned {count} temporary chunk directories physically successfully!")
    else:
        print("Temporary directory not found.")

if __name__ == "__main__":
    main()
