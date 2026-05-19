"""
批次垃圾與矩陣對照組製造器 (GC Matrix & Bulk Garbage Generator)
職責：
1. 查詢合法 owner_id 防止 SQLite 外鍵約束報錯。
2. 設計 5 大精準測試矩陣（包含過期/活躍、有物理目錄/無物理目錄、資料庫與孤立組合）。
3. 批次產生大量垃圾（預設每種組合 10 個，共 50 個測試案例），全面壓測與驗證背景 GC 哨兵之穩健性。
"""
import os
import sqlite3
import uuid
import time
import shutil
from datetime import datetime, timedelta, timezone

# 測試配置：每種組合產生的數量
BATCH_SIZE = 10 

def main():
    # 1. 動態推算專案根目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    db_path = os.path.join(project_root, "db", "file_explorer.db")
    temp_dir = os.path.join(project_root, "data", "temp")
    
    print("=" * 70)
    print("🚀 啟動 [GC 批次垃圾與矩陣測試製造器]...")
    print(f"📌 資料庫路徑: {db_path}")
    print(f"📌 暫存資料夾: {temp_dir}")
    print(f"📌 製造批次量: 每種組合 {BATCH_SIZE} 個，共計 {BATCH_SIZE * 5} 個測試案例！")
    print("=" * 70)

    # 確保暫存目錄存在
    os.makedirs(temp_dir, exist_ok=True)

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
    db_inserts = []
    physical_folders = []

    print("\n--- 🏗️ 開始建立矩陣測試案例 ---")

    # =========================================================================
    # 組合 1：DB已過期 + 有物理目錄 (Type 1: DB_EXPIRED_WITH_PHYSICAL)
    # 🎯 預期結果：DB被刪除，實體資料夾被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 1 [DB已過期 + 有物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-exp-phys-{uuid.uuid4().hex[:6]}"
        db_inserts.append((u_id, owner_id, "db_expired_with_phys.bin", 3, db_expired_time))
        
        # 物理目錄 (過期時間)
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"expired chunk data")
        os.utime(p_path, (past_30_hours, past_30_hours))
        physical_folders.append(p_path)

    # =========================================================================
    # 組合 2：DB未過期 + 有物理目錄 (Type 2: DB_FRESH_WITH_PHYSICAL)
    # 🎯 預期結果：🟢 完美安全保護！DB 與 實體資料夾皆保留！
    # =========================================================================
    print(f"➡️ 製造 組合 2 [DB未過期 + 有物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-frsh-phys-{uuid.uuid4().hex[:6]}"
        db_inserts.append((u_id, owner_id, "db_fresh_with_phys.bin", 5, db_fresh_time))
        
        # 物理目錄 (活躍時間)
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"fresh chunk data")
        os.utime(p_path, (past_5_mins, past_5_mins))
        physical_folders.append(p_path)

    # =========================================================================
    # 組合 3：DB已過期 + 無物理目錄 (Type 3: DB_EXPIRED_NO_PHYSICAL)
    # 🎯 預期結果：DB被刪除，且 GC 執行中不可因為找不到物理目錄而崩潰！
    # =========================================================================
    print(f"➡️ 製造 組合 3 [DB已過期 + 無物理目錄] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-db-exp-nophys-{uuid.uuid4().hex[:6]}"
        db_inserts.append((u_id, owner_id, "db_expired_no_phys.bin", 3, db_expired_time))
        # 不建立物理目錄

    # =========================================================================
    # 組合 4：物理孤立目錄 + 已過期 (Type 4: PHYSICAL_ORPHANED_EXPIRED)
    # 🎯 預期結果：實體資料夾被刪除！
    # =========================================================================
    print(f"➡️ 製造 組合 4 [物理孤立目錄 + 已過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-orph-exp-{uuid.uuid4().hex[:6]}"
        # 不寫入資料庫
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"orphaned old chunk")
        os.utime(p_path, (past_30_hours, past_30_hours))
        physical_folders.append(p_path)

    # =========================================================================
    # 組合 5：物理孤立目錄 + 未過期 (Type 5: PHYSICAL_ORPHANED_FRESH)
    # 🎯 預期結果：🟢 完美安全保護！實體資料夾必須保留（防誤殺）！
    # =========================================================================
    print(f"➡️ 製造 組合 5 [物理孤立目錄 + 未過期] x {BATCH_SIZE}...")
    for _ in range(BATCH_SIZE):
        u_id = f"test-gc-orph-frsh-{uuid.uuid4().hex[:6]}"
        # 不寫入資料庫
        p_path = os.path.join(temp_dir, u_id)
        os.makedirs(p_path, exist_ok=True)
        with open(os.path.join(p_path, "0"), "wb") as f:
            f.write(b"orphaned fresh chunk")
        os.utime(p_path, (past_5_mins, past_5_mins))
        physical_folders.append(p_path)

    # 3. 將資料批次寫入資料庫
    if os.path.exists(db_path) and db_inserts:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO upload_sessions (id, owner_id, filename, total_chunks, created_at) VALUES (?, ?, ?, ?, ?)",
                db_inserts
            )
            conn.commit()
            conn.close()
            print(f"\n✅ 成功將 {len(db_inserts)} 筆對照組會話寫入 SQLite 資料庫！")
        except Exception as e:
            print(f"\n❌ 批次寫入 SQLite 失敗: {e}")
    else:
        print("\n⚠️ 找不到資料庫檔案，僅產生了本地物理目錄垃圾。")

    # 4. 輸出最終對照面板供開發者驗證
    print("\n" + "=" * 70)
    print("📊 垃圾製造完成！測試對照組面板：")
    print("-" * 70)
    print(f" 組合 1 [DB過期+有物理] : 預期 DB 刪除 / 實體刪除 ── 製造數: {BATCH_SIZE}")
    print(f" 組合 2 [DB活躍+有物理] : 預期 🟢 雙重安全保留    ── 製造數: {BATCH_SIZE}")
    print(f" 組合 3 [DB過期+無物理] : 預期 DB 刪除 / 容錯不崩潰 ── 製造數: {BATCH_SIZE}")
    print(f" 組合 4 [孤立過期目錄]   : 預期 實體刪除            ── 製造數: {BATCH_SIZE}")
    print(f" 組合 5 [孤立活躍目錄]   : 預期 🟢 實體安全保留     ── 製造數: {BATCH_SIZE}")
    print("=" * 70)
    print("👉 請確保伺服器執行中，觀察 GC 哨兵運作。")
    print("👉 盤點完成後，您可以重新執行 `clean_sessions.py` 一鍵還原乾淨環境！")
    print("=" * 70)

if __name__ == "__main__":
    main()
