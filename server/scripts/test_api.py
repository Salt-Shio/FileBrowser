import requests
import json
import hashlib
import io

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

def test_get_me(token):
    print("\n[測試] GET /auth/me")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_ls(token, folder_id=None):
    print(f"\n[測試] GET /vfs/ls (folder_id={folder_id})")
    headers = {"Authorization": f"Bearer {token}"}
    params = {"folder_id": folder_id} if folder_id else {}
    response = requests.get(f"{BASE_URL}/vfs/ls", headers=headers, params=params)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    return response.json()

def test_vfs_search(token, query):
    print(f"\n[測試] GET /vfs/search (q={query})")
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query}
    response = requests.get(f"{BASE_URL}/vfs/search", headers=headers, params=params)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_mkdir(token, name, parent_id=None):
    if name.lower() == "no": return None

    print(f"\n[測試] POST /vfs/mkdir (name={name}, parent_id={parent_id})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"name": name, "parent_id": parent_id}
    response = requests.post(f"{BASE_URL}/vfs/mkdir", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    return response.json()

def test_vfs_delete(token, node_id, node_type):
    print(f"\n[測試] POST /vfs/delete (id={node_id}, type={node_type})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "node_id": node_id,
        "node_type": node_type
    }
    response = requests.post(f"{BASE_URL}/vfs/delete", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_rename(token, node_id, node_type, new_name):
    print(f"\n[測試] POST /vfs/rename (id={node_id}, type={node_type}, new_name={new_name})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "node_id": node_id,
        "node_type": node_type,
        "new_name": new_name
    }
    response = requests.post(f"{BASE_URL}/vfs/rename", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_move(token, node_id, node_type, target_parent_id):
    print(f"\n[測試] POST /vfs/move (id={node_id}, type={node_type}, target_parent={target_parent_id})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "node_id": node_id,
        "node_type": node_type,
        "target_parent_id": target_parent_id
    }
    response = requests.post(f"{BASE_URL}/vfs/move", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_upload(token, filename="chunk_test.txt", target_folder_id=None):
    print(f"\n[測試] 開始三階段分塊上傳檔案: {filename}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 產生模擬檔案內容與計算預期 SHA256
    import os
    file_content = b"Hello, Antigravity! This is a test file for chunked uploading. It consists of multiple chunks to test stream merging and integrity checks." + os.urandom(1024 * 1024 * 10)
    expected_hash = hashlib.sha256(file_content).hexdigest()
    
    # 進行切分上傳，每塊 2MB
    chunk_size = 2 * 1024 * 1024
    chunks = [file_content[i:i+chunk_size] for i in range(0, len(file_content), chunk_size)]
    total_chunks = len(chunks)
    print(f"    模擬檔案大小: {len(file_content)} bytes, 將切分為 {total_chunks} 個分塊上傳。")
    print(f"    預期雜湊 (SHA256): {expected_hash}")
    
    # 2. 第一階段：初始化上傳會話
    print("\n    --> [階段一] 初始化上傳會話 (POST /vfs/upload/init)...")
    init_payload = {
        "filename": filename,
        "total_chunks": total_chunks,
        "expected_hash": expected_hash,
        "target_folder_id": target_folder_id
    }
    init_res = requests.post(f"{BASE_URL}/vfs/upload/init", headers=headers, json=init_payload)
    print(f"    狀態碼: {init_res.status_code}")
    print(f"    回應: {json.dumps(init_res.json(), indent=4, ensure_ascii=False)}")
    
    if init_res.status_code != 201:
        print("    [!] 初始化上傳失敗，終止測試。")
        return
        
    upload_id = init_res.json()["upload_id"]
    
    # 3. 第二階段：流式上傳所有分塊
    print(f"\n    --> [階段二] 流式上傳分塊 (POST /vfs/upload/chunk)...")
    for idx, chunk_data in enumerate(chunks):
        print(f"        上傳分塊 [{idx + 1}/{total_chunks}] 大小: {len(chunk_data)} bytes...")
        
        # 準備 multipart/form-data
        files = {
            "file": (f"chunk_{idx}", io.BytesIO(chunk_data), "application/octet-stream")
        }
        data = {
            "upload_id": upload_id,
            "chunk_index": idx
        }
        chunk_res = requests.post(f"{BASE_URL}/vfs/upload/chunk", headers=headers, data=data, files=files)
        print(f"        分塊 [{idx + 1}] 上傳狀態碼: {chunk_res.status_code} | 回應: {chunk_res.json()}")
        if chunk_res.status_code != 200:
            print("        [!] 分塊上傳失敗，終止測試。")
            return
            
    # 4. 第三階段：結算合併入籍
    print("\n    --> [階段三] 檔案合併與入籍結算 (POST /vfs/upload/finalize)...")
    finalize_payload = {
        "upload_id": upload_id
    }
    finalize_res = requests.post(f"{BASE_URL}/vfs/upload/finalize", headers=headers, json=finalize_payload)
    print(f"    狀態碼: {finalize_res.status_code}")
    print(f"    回應: {json.dumps(finalize_res.json(), indent=4, ensure_ascii=False)}")
    
    if finalize_res.status_code == 200:
        print("\n🎉 [測試成功] 分塊上傳與 VFS 檔案入籍已順利完成！")
    else:
        print("\n❌ [測試失敗] 檔案結算入籍失敗。")

def main():
    # --- 1. 認證流程 ---
    two_fa_token = login(input("user: "), input("password: "))
    if not two_fa_token:
        return

    access_token = verify_2fa(two_fa_token)
    if not access_token:
        return

    # --- 2. 開始功能測試 (這部分你可以隨意註解或修改) ---
    
    # 測試獲取個人資訊
    test_get_me(access_token)

    # 測試列出根目錄
    ls_data = test_vfs_ls(access_token)

    # 測試搜尋
    test_vfs_search(access_token, "Root")

    # 測試建立資料夾
    new_folder = test_vfs_mkdir(access_token, input("輸入資料夾: "), input("父資料夾 ID: "))
    
    test_vfs_rename(access_token, input("Rename Node ID: "), "folder", input("更名後的名稱: "))
    
    # 測試搬移功能
    test_vfs_move(access_token, input("Move Node ID: "), "folder", input("目標父目錄 ID: "))
    
    # 測試刪除
    test_vfs_delete(access_token, input("Delete Node ID: "), "folder")

    # 測試分塊上傳功能
    do_upload = input("\n是否測試三階段分塊上傳功能 (y/n)? ")
    if do_upload.lower() == "y":
        filename = input("    請輸入測試上傳的檔名 (預設: chunk_test.txt): ") or "chunk_test.txt"
        target_folder = input("    請輸入目標資料夾 ID (直接 Enter 則上傳至 Root): ") or None
        test_vfs_upload(access_token, filename=filename, target_folder_id=target_folder)

    # 再次列出查看結果
    test_vfs_ls(access_token)

if __name__ == "__main__":
    main()
