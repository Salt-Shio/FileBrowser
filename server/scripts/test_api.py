import requests
import json

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

def test_vfs_rename(token, node_id, node_type, new_name):
    print(f"\n[測試] PATCH /vfs/rename (id={node_id}, type={node_type}, new_name={new_name})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "node_id": node_id,
        "node_type": node_type,
        "new_name": new_name
    }
    response = requests.patch(f"{BASE_URL}/vfs/rename", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

def test_vfs_move(token, node_id, node_type, target_parent_id):
    print(f"\n[測試] PATCH /vfs/move (id={node_id}, type={node_type}, target_parent={target_parent_id})")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "node_id": node_id,
        "node_type": node_type,
        "target_parent_id": target_parent_id
    }
    response = requests.patch(f"{BASE_URL}/vfs/move", headers=headers, json=payload)
    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

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
        
    # 再次列出查看結果
    test_vfs_ls(access_token)

if __name__ == "__main__":
    main()
