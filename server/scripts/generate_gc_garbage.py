"""
批次垃圾與矩陣對照組製造器 (GC Matrix & Bulk Garbage Generator)
職責：
1. 查詢合法 owner_id 防止 SQLite 外鍵約束報錯。
2. 設計 9 大精準測試矩陣（包含會話過期/活躍、暫存區孤立資料夾、已軟刪除檔案與目錄過期對照組）。
3. 批次產生大量垃圾（預設每種組合 10 個，共 90 個測試案例），全面驗證背景 GC 各清理動作的穩健性。
"""
import os
import sqlite3
import uuid
import time
from datetime import datetime, timedelta, timezone

# 測試配置：每種組合產生的數量
BATCH_SIZE = 10 

def main():
    # 1. 動態推算專案根目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    db_path = os.path.join(project_root, "db", "file_explorer.db")
    temp_dir = os.path.join(project_root, "data", "temp")
    uploads_dir = os.path.join(project_root, "data", "uploads")
    
    print("=" * 70)
    print("🚀 啟動 [GC 批次垃圾與矩陣測試製造器]...")
    print(f"📌 資料庫路徑: {db_path}")
    print(f"📌 暫存資料夾: {temp_dir}")
    print(f"📌 上傳資料夾: {uploads_dir}")
    print(f"📌 製造批次量: 每種組合 {BATCH_SIZE} 個，共計 {BATCH_SIZE * 9} 個測試案例！")
    print("=" * 70)

    # 確保目錄存在
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)

    # 2. 獲取一個合法的使用者 ID 防止 SQLite 外鍵約束報錯
    owner_id = None
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users LIMIT 1")
            row = cursor.fetchone()
            if row:
                owner_id = row[0]
                print(f"🔑 成功獲取資料庫合法 owner_id: {owner_id}")
            else:
                print("⚠️ 資料庫中無使用者，將生成隨機模擬 owner_id。")
            conn.close()
        except Exception as e:
            print(f"❌ 查詢使用者失敗: {e}")

    if not owner_id:
        owner_id = str(uuid.uuid4())
        print(f"⚠️ 使用隨機模擬 owner_id: {owner_id}")

    # 時間計算
    now = time.time()
    past_30_hours = now - (30 * 3600)  # 30 小時前 (過期)
    past_5_mins = now - 300            # 5 分鐘前 (活躍)
    
    db_expired_time = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S.%f")
    db_fresh_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S.%f")

    # 用於統計寫入
    session_inserts = []
    file_inserts = []
    folder_inserts = []

    print("\n--- 🏗️ 開始建立矩陣測試案例 ---")

    # =========================================================================
    # 組合 1：DB已過期 + 有物理目錄 (Type 1: DB_EXPIRED_WITH_PHYSICAL)
    # 🎯 預期結果：DB被刪除，實體資料夾被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 1 [DB已過期 + 有物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-exp-phys-{uuid.uuid4().hex[:6]}"
        session_inserts.append((u_id, owner_id, "db_expired_with_phys.bin", 3, db_expired_time))
        
        # 物理目錄 (過期時間)
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"expired chunk data")
        os.utime(p_path, (past_30_hours, past_30_hours))

    # =========================================================================
    # 組合 2：DB未過期 + 有物理目錄 (Type 2: DB_FRESH_WITH_PHYSICAL)
    # 🎯 預期結果：🟢 完美安全保護！DB 與 實體資料夾皆保留！
    # =========================================================================
    print(f"➡️ 製造 組合 2 [DB未過期 + 有物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-frsh-phys-{uuid.uuid4().hex[:6]}"
        session_inserts.append((u_id, owner_id, "db_fresh_with_phys.bin", 5, db_fresh_time))
        
        # 物理目錄 (活躍時間)
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"fresh chunk data")
        os.utime(p_path, (past_5_mins, past_5_mins))

    # =========================================================================
    # 組合 3：DB已過期 + 無物理目錄 (Type 3: DB_EXPIRED_NO_PHYSICAL)
    # 🎯 預期結果：DB被刪除，且 GC 執行中不可因為找不到物理目錄而崩潰！
    # =========================================================================
    print(f"➡️ 製造 組合 3 [DB已過期 + 無物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-exp-nophys-{uuid.uuid4().hex[:6]}"
        session_inserts.append((u_id, owner_id, "db_expired_no_phys.bin", 3, db_expired_time))

    # =========================================================================
    # 組合 4：物理孤立目錄 + 已過期 (Type 4: PHYSICAL_ORPHANED_EXPIRED)
    # 🎯 預期結果：實體資料夾被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 4 [物理孤立目錄 + 已過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-orph-exp-{uuid.uuid4().hex[:6]}"
        # 不寫入資料庫，僅建立物理目錄
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"orphaned old chunk")
        os.utime(p_path, (past_30_hours, past_30_hours))

    # =========================================================================
    # 組合 5：物理孤立目錄 + 未過期 (Type 5: PHYSICAL_ORPHANED_FRESH)
    # 🎯 預期結果：🟢 完美安全保護！實體資料夾必須保留（防誤殺）！
    # =========================================================================
    print(f"➡️ 製造 組合 5 [物理孤立目錄 + 未過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-orph-frsh-{uuid.uuid4().hex[:6]}"
        # 不寫入資料庫，僅建立物理目錄
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"orphaned fresh chunk")
        os.utime(p_path, (past_5_mins, past_5_mins))

    # =========================================================================
    # 組合 6：邏輯已刪除檔案 + 已過期 (Type 6: FILE_DELETED_EXPIRED)
    # 🎯 預期結果：DB被刪除，且 data/uploads 下的物理檔案被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 6 [邏輯已刪除檔案 + 已過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-file-exp-{uuid.uuid4().hex[:6]}"
        storage_name = f"test-file-exp-{uuid.uuid4().hex[:6]}.dat"
        file_inserts.append((
            u_id, "expired_deleted_file.txt", None, owner_id, 1024, "text/plain",
            storage_name, "mocksha256expiredfile", db_expired_time, db_expired_time, 1, db_expired_time
        ))
        # 建立物理檔案
        fp = os.path.join(uploads_dir, storage_name)
        with open(fp, "wb") as f:
            f.write(b"expired deleted file physical contents")

    # =========================================================================
    # 組合 7：邏輯已刪除檔案 + 未過期 (Type 7: FILE_DELETED_FRESH)
    # 🎯 預期結果：🟢 完美安全保護！DB 與 實體正式檔案皆保留！
    # =========================================================================
    print(f"➡️ 製造 組合 7 [邏輯已刪除檔案 + 未過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-file-frsh-{uuid.uuid4().hex[:6]}"
        storage_name = f"test-file-frsh-{uuid.uuid4().hex[:6]}.dat"
        file_inserts.append((
            u_id, "fresh_deleted_file.txt", None, owner_id, 2048, "text/plain",
            storage_name, "mocksha256freshfile", db_fresh_time, db_fresh_time, 1, db_fresh_time
        ))
        # 建立物理檔案
        fp = os.path.join(uploads_dir, storage_name)
        with open(fp, "wb") as f:
            f.write(b"fresh deleted file physical contents")

    # =========================================================================
    # 組合 8：邏輯已刪除目錄 + 已過期 (Type 8: FOLDER_DELETED_EXPIRED)
    # 🎯 預期結果：DB被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 8 [邏輯已刪除目錄 + 已過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-fold-exp-{uuid.uuid4().hex[:6]}"
        folder_inserts.append((
            u_id, "expired_deleted_folder", None, owner_id, db_expired_time, db_expired_time, 1, db_expired_time
        ))

    # =========================================================================
    # 組合 9：邏輯已刪除目錄 + 未過期 (Type 9: FOLDER_DELETED_FRESH)
    # 🎯 預期結果：🟢 完美安全保護！DB 記錄保留！
    # =========================================================================
    print(f"➡️ 製造 組合 9 [邏輯已刪除目錄 + 未過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-fold-frsh-{uuid.uuid4().hex[:6]}"
        folder_inserts.append((
            u_id, "fresh_deleted_folder", None, owner_id, db_fresh_time, db_fresh_time, 1, db_fresh_time
        ))

    # 3. 將資料批次寫入資料庫
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 寫入會話
            if session_inserts:
                cursor.executemany(
                    "INSERT INTO upload_sessions (id, owner_id, filename, total_chunks, created_at) VALUES (?, ?, ?, ?, ?)",
                    session_inserts
                )
            
            # 寫入檔案
            if file_inserts:
                cursor.executemany(
                    "INSERT INTO files (id, name, folder_id, owner_id, size, mime_type, storage_path, hash_sha256, created_at, updated_at, is_deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    file_inserts
                )
                
            # 寫入目錄
            if folder_inserts:
                cursor.executemany(
                    "INSERT INTO folders (id, name, parent_id, owner_id, created_at, updated_at, is_deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    folder_inserts
                )
                
            conn.commit()
            conn.close()
            print(f"\n✅ 成功寫入資料庫：{len(session_inserts)} 筆會話、{len(file_inserts)} 筆檔案、{len(folder_inserts)} 筆目錄！")
        except Exception as e:
            print(f"\n❌ 批次寫入 SQLite 失敗: {e}")
    else:
        print("\n⚠️ 找不到資料庫檔案，僅產生了本地物理目錄垃圾。")

    # 4. 輸出最終對照面板供開發者驗證
    print("\n" + "=" * 80)
    print("📊 垃圾製造完成！測試對照組面板：")
    print("-" * 80)
    print(f" 組合 1 [DB會話過期+有物理] : 預期 DB 刪除 / 暫存刪除  ── 製造數: {BATCH_SIZE}")
    print(f" 組合 2 [DB會話活躍+有物理] : 預期 🟢 雙重安全保留       ── 製造數: {BATCH_SIZE}")
    print(f" 組合 3 [DB會話過期+無物理] : 預期 DB 刪除 / 容錯不崩潰  ── 製造數: {BATCH_SIZE}")
    print(f" 組合 4 [孤立過期暫存目錄]   : 預期 暫存刪除             ── 製造數: {BATCH_SIZE}")
    print(f" 組合 5 [孤立活躍暫存目錄]   : 預期 🟢 暫存安全保留      ── 製造數: {BATCH_SIZE}")
    print(f" 組合 6 [邏輯刪除檔案+已過期] : 預期 DB 刪除 / 實體刪除  ── 製造數: {BATCH_SIZE}")
    print(f" 組合 7 [邏輯刪除檔案+未過期] : 預期 🟢 DB/實體安全保留  ── 製造數: {BATCH_SIZE}")
    print(f" 組合 8 [邏輯刪除目錄+已過期] : 預期 DB 刪除            ── 製造數: {BATCH_SIZE}")
    print(f" 組合 9 [邏輯刪除目錄+未過期] : 預期 🟢 DB 安全保留       ── 製造數: {BATCH_SIZE}")
    print("=" * 80)
    print("👉 請確保伺服器執行中，觀察 GC 哨兵運作。")
    print("👉 盤點完成後，您可以重新執行 `clean_sessions.py` 一鍵還原乾淨環境！")
    print("=" * 80)

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
