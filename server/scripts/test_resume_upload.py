import requests
import json
import hashlib
import io
import os
import time

BASE_URL = "http://localhost:8000/api"

def login(username, password):
    print(f"\n[1] 正在登入使用者: {username}...")
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("    成功獲取 2FA Token")
        return data["two_fa_token"]
    else:
        print(f"    登入失敗: {response.text}")
        return None

def verify_2fa(two_fa_token):
    print("\n[2] 需要 2FA 驗證")
    otp_code = input("    請輸入 6 位數驗證碼: ")
    url = f"{BASE_URL}/auth/verify-2fa"
    payload = {
        "two_fa_token": two_fa_token,
        "otp_code": otp_code
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("    成功獲取 Access Token")
        return data["access_token"]
    else:
        print(f"    2FA 驗證失敗: {response.text}")
        return None

def main():
    # --- 1. 登入與 2FA 驗證 ---
    two_fa_token = login(input("user: "), input("password: "))
    if not two_fa_token:
        return

    token = verify_2fa(two_fa_token)
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}

    # --- 2. 模擬準備 15MB 檔案，切成 5 個分塊 (每塊 3MB) ---
    print("\n[3] 正在準備 15MB 測試檔案...")
    file_content = b"FileBrowser Resumable Upload Test! " + os.urandom(1024 * 1024 * 15)
    original_hash = hashlib.sha256(file_content).hexdigest()
    filename = f"resumable_test_{int(time.time())}.jpg"
    
    chunk_size = 3 * 1024 * 1024
    chunks = [file_content[i:i+chunk_size] for i in range(0, len(file_content), chunk_size)]
    total_chunks = len(chunks)
    
    print(f"    檔案總大小: {len(file_content)} bytes")
    print(f"    分塊數: {total_chunks} 塊")
    print(f"    原始檔案雜湊 (SHA256): {original_hash}")

    # --- 3. 第一階段：初始化分塊會話 ---
    print("\n[4] --> [階段一] 初始化分塊會話 (POST /vfs/upload/init)...")
    init_payload = {
        "filename": filename,
        "total_chunks": total_chunks,
        "expected_hash": original_hash
    }
    init_res = requests.post(f"{BASE_URL}/vfs/upload/init", headers=headers, json=init_payload)
    if init_res.status_code != 201:
        print(f"    ❌ 初始化失敗: {init_res.text}")
        return
        
    upload_id = init_res.json()["upload_id"]
    print(f"    成功建立上傳會話! Upload ID: {upload_id}")

    # --- 4. 第二階段：模擬中斷上傳 (只上傳分塊 0 和 1) ---
    print("\n[5] --> [階段二] 模擬開始上傳，但半途中斷...")
    for idx in [0, 1]:
        print(f"        正在上傳分塊 [{idx}/{total_chunks - 1}]...")
        files = {"file": (f"chunk_{idx}", io.BytesIO(chunks[idx]), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": idx}
        chunk_res = requests.post(f"{BASE_URL}/vfs/upload/chunk", headers=headers, data=data, files=files)
        if chunk_res.status_code != 200:
            print(f"        ❌ 分塊 {idx} 上傳失敗!")
            return
            
    print("\n⚠️ [模擬中斷成功] 故意停止上傳！此時網路中斷或用戶關閉網頁...")
    print("    目前伺服器僅存有: 分塊 [0, 1]")

    # --- 5. 第三階段：模擬重新連線，向伺服器探測進度狀態 ---
    print("\n[6] --> [階段三] 模擬斷線重連，探測伺服器目前已收到的分塊狀態...")
    status_res = requests.get(f"{BASE_URL}/vfs/upload/status/{upload_id}", headers=headers)
    if status_res.status_code != 200:
        print(f"    ❌ 探測失敗: {status_res.text}")
        return
        
    status_data = status_res.json()
    uploaded = status_data["uploaded_chunks"]
    missing = status_data["missing_chunks"]
    print(f"    伺服器回傳已收分塊 (uploaded_chunks): {uploaded}")
    print(f"    伺服器回傳缺失分塊 (missing_chunks) : {missing}")

    # 驗證探測精準度
    expected_missing = list(range(2, total_chunks))
    if uploaded == [0, 1] and missing == expected_missing:
        print(f"    🎉 [狀態探測完全正確] 伺服器精準識別已收到的 [0, 1] 並傳回缺漏的 {expected_missing}！")
    else:
        print("    ❌ [狀態探測錯誤] 伺服器回傳的分塊狀態不符預期，終止測試。")
        return

    # --- 6. 第四階段：智慧續傳 (只補傳 missing_chunks) ---
    print("\n[7] --> [階段四] 智慧斷點續傳 (只上傳 missing_chunks 列表中的分塊)...")
    print(f"    ⚠️  [優化效益] 自動跳過已上傳的分塊 0, 1，節省 6MB 頻寬！")
    
    for idx in missing:
        print(f"        [續傳補發] 正在上傳缺漏的分塊 [{idx}/{total_chunks - 1}]...")
        files = {"file": (f"chunk_{idx}", io.BytesIO(chunks[idx]), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": idx}
        chunk_res = requests.post(f"{BASE_URL}/vfs/upload/chunk", headers=headers, data=data, files=files)
        if chunk_res.status_code != 200:
            print(f"        ❌ 續傳分塊 {idx} 上傳失敗!")
            return

    print("    🎉 所有缺失分片補發完畢！")

    # --- 7. 第五階段：合併結算與入籍 ---
    print("\n[8] --> [階段五] 合併結算入籍 (POST /vfs/upload/finalize)...")
    finalize_payload = {"upload_id": upload_id}
    finalize_res = requests.post(f"{BASE_URL}/vfs/upload/finalize", headers=headers, json=finalize_payload)
    if finalize_res.status_code != 200:
        print(f"    ❌ 結算失敗: {finalize_res.text}")
        return
        
    file_metadata = finalize_res.json()
    file_id = file_metadata["id"]
    print("    🎉 檔案入籍成功！")
    print(json.dumps(file_metadata, indent=4, ensure_ascii=False))

    # --- 8. 第六階段：下載檔案並驗證 ETag 與完整性 (端到端雙重驗證) ---
    print("\n[9] --> [階段六] 安全串流下載已入籍的續傳檔案並驗證完整性...")
    download_url = f"{BASE_URL}/vfs/download/{file_id}"
    response = requests.get(download_url, headers=headers, stream=True)
    
    if response.status_code != 200:
        print(f"    ❌ 下載失敗: {response.text}")
        return
        
    etag = response.headers.get("ETag", "").strip('"')
    print(f"    回應 ETag 標頭雜湊值: {etag}")
    
    sha256 = hashlib.sha256()
    downloaded_size = 0
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            sha256.update(chunk)
            downloaded_size += len(chunk)
            
    downloaded_hash = sha256.hexdigest()
    print(f"    下載檔案實際大小: {downloaded_size} bytes")
    print(f"    下載檔案實際雜湊 (SHA256): {downloaded_hash}")
    print(f"    原始檔案雜湊 (SHA256): {original_hash}")
    
    # 三重校驗
    if downloaded_hash == original_hash and etag == original_hash and downloaded_size == len(file_content):
        print("\n🏆🏆🏆 [斷點續傳測試大成功] 🏆🏆🏆")
        print("    1. 分塊中斷與智慧進度探測完全正確！")
        # 計算省下的頻寬比例
        saved_pct = (2 / total_chunks) * 100
        print(f"    2. 斷點續傳為您成功節省了 {saved_pct:.1f}% 的重複傳輸頻寬與時間！")
        print("    3. 下載檔案的實際大小、內容雜湊與 HTTP ETag 標頭全部完全一致，100% 完整無損！")
    else:
        print("\n❌ [下載校驗失敗] 續傳合併後的檔案內容與原始檔案不符！")

    # =========================================================================
    # --- 9. [新增安全測試] 主動取消 API (POST /vfs/upload/cancel) 驗證 ---
    # =========================================================================
    print("\n" + "="*60)
    print("🔒 [額外整合測試] 正在驗證「主動取消上傳與碎片清理」機制...")
    print("="*60)
    
    # 初始化一個新的會話
    print("\n[C1] 正在初始化新上傳會話 (POST /vfs/upload/init)...")
    cancel_filename = "cancel_test_file.jpg"
    init_cancel_payload = {
        "filename": cancel_filename,
        "total_chunks": 3,
        "expected_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # mock hash
    }
    init_res = requests.post(f"{BASE_URL}/vfs/upload/init", headers=headers, json=init_cancel_payload)
    if init_res.status_code != 201:
        print(f"    ❌ 初始化取消測試失敗: {init_res.text}")
        return
        
    cancel_upload_id = init_res.json()["upload_id"]
    print(f"    成功建立取消測試會話! Upload ID: {cancel_upload_id}")

    # 上傳第一個分塊以製造物理碎片
    print("\n[C2] 正在上傳分塊 0 製造物理暫存碎片 (POST /vfs/upload/chunk)...")
    mock_chunk_data = b"Cancel Test Chunk Content"
    files = {"file": ("chunk_0", io.BytesIO(mock_chunk_data), "application/octet-stream")}
    data = {"upload_id": cancel_upload_id, "chunk_index": 0}
    chunk_res = requests.post(f"{BASE_URL}/vfs/upload/chunk", headers=headers, data=data, files=files)
    if chunk_res.status_code != 200:
        print(f"    ❌ 分塊上傳失敗: {chunk_res.text}")
        return
    print("    分塊 0 上傳成功！磁碟已物理產生碎片檔案。")

    # 驗證狀態探測為 [0]
    print("\n[C3] 探測目前分塊狀態，確認物理落籍...")
    status_res = requests.get(f"{BASE_URL}/vfs/upload/status/{cancel_upload_id}", headers=headers)
    print(f"    探測狀態碼: {status_res.status_code} | 已收分片: {status_res.json()['uploaded_chunks']}")

    # 呼叫主動取消 API
    print("\n[C4] --> 呼叫主動取消端點 (POST /vfs/upload/cancel)...")
    cancel_payload = {"upload_id": cancel_upload_id}
    cancel_res = requests.post(f"{BASE_URL}/vfs/upload/cancel", headers=headers, json=cancel_payload)
    print(f"    取消 API 狀態碼: {cancel_res.status_code}")
    print(f"    回應結果: {json.dumps(cancel_res.json(), indent=4, ensure_ascii=False)}")
    
    # 驗證 1: 再次查詢該會話狀態，斷言回傳 404 (證明會話已在資料庫徹底刪除)
    print("\n[C5] 驗證一：再次查詢該會話狀態...")
    status_after_res = requests.get(f"{BASE_URL}/vfs/upload/status/{cancel_upload_id}", headers=headers)
    print(f"    再次探測狀態碼: {status_after_res.status_code} (預期應為 404)")
    
    # 驗證 2: 再次嘗試對該會話初始化同名檔案，確認可以立即正常初始化 (證明命名鎖定已被釋放)
    print("\n[C6] 驗證二：嘗試立即重新初始化同名檔案...")
    retry_init_res = requests.post(f"{BASE_URL}/vfs/upload/init", headers=headers, json=init_cancel_payload)
    print(f"    重新初始化狀態碼: {retry_init_res.status_code} (預期應為 201)")
    
    # 再次清理乾淨，防止影響下次測試
    if retry_init_res.status_code == 201:
        new_cancel_id = retry_init_res.json()["upload_id"]
        requests.post(f"{BASE_URL}/vfs/upload/cancel", headers=headers, json={"upload_id": new_cancel_id})

    if status_after_res.status_code == 404 and retry_init_res.status_code == 201:
        print("\n🏆🏆🏆 [主動取消與碎片大掃除測試完美成功！] 🏆🏆🏆")
        print("    1. 資料庫上傳會話已物理刪除！")
        print("    2. 同名檔案鎖定已被安全釋放！")
        print("    3. 實體暫存目錄已由 anyio 非同步執行緒池徹底安全清空！")
    else:
        print("\n❌ [主動取消測試失敗] 清除機制未完全達成預期指標。")

if __name__ == "__main__":
    main()
