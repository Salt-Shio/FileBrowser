# File Explorer

一個用來做檔案上傳的個人網站，方便自己遠端操作

但實作的方式，我希望更貼近大專案的想法與做法

## 系統架構

```mermaid
graph TD
    %% 外部請求流向
    User([個人使用者]) -- HTTPS (CF Edge) --> CF_Tunnel[Cloudflare Tunnel]
    
    subgraph Docker_Boundary [Docker 部署邊界]
        CF_Tunnel -- Secure Tunnel --> Ingress
        
        subgraph Layer_1 [1. 流量閘道層]
            Ingress[安全攔截器: 限流 / CF-IP 識別]
            Router[API 總路由器]
            Ingress --> Router
        end

    %% 第二層：具體業務端點 (Features)
    subgraph Layer_2 [2. 具體功能端點]
        direction LR
        subgraph Auth_Endpoints [認證管理]
            EP_Register[註冊帳號]
            EP_Login[登入介面]
            EP_2FA[2FA 驗證]
        end
        subgraph File_Endpoints [檔案與目錄操作]
            EP_Browse[瀏覽與搜尋: List/Search]
            EP_Download[檔案下載]
            EP_Upload[檔案上傳]
            EP_Modify[位置/名稱修改: Move/Rename]
            EP_Mkdir[建立資料夾]
            EP_Delete[刪除功能]
        end
    end

    Router --> Auth_Endpoints
    Router --> File_Endpoints

    %% 第三層：核心業務引擎 (Engines) & 背景維護
    subgraph Layer_3_Auth [3. 認證與權限引擎]
        Auth_Core[驗證核心: TOTP / Argon2]
        Session_Mgr[會話管理器: JWT 簽發]
        Auth_Core --> Session_Mgr
    end

    subgraph Layer_3_File [4. 檔案引擎核心]
        VFS_Engine[VFS 核心引擎: 結構管理與實體同步]
        Chunk_Mgr[Chunk_Mgr: 分片處理與合併]
        
        %% 內部邏輯流
        VFS_Engine -. 權限驗證 .-> Chunk_Mgr
        Chunk_Mgr -- 合併完成 --> VFS_Engine
    end

    subgraph Layer_3_GC [背景維護核心]
        GC_Sentinel[背景 GC 哨兵: 定期大掃除]
    end

    %% 第四層：數據持久化
    subgraph Layer_4 [5. 數據持久層]
        DB[(SQLite: Metadata / 使用者)]
        Disk[實體磁碟: 二進制檔案]
    end

    %% 跨層對接邏輯
    EP_Register --> Auth_Core
    EP_Login --> Auth_Core
    EP_2FA --> Auth_Core
    
    %% 檔案操作：統一對接 VFS 引擎
    EP_Browse --> VFS_Engine
    EP_Download --> VFS_Engine
    EP_Upload --> VFS_Engine
    EP_Modify --> VFS_Engine
    EP_Mkdir --> VFS_Engine
    EP_Delete --> VFS_Engine

    %% 背景 GC 哨兵運作關聯
    GC_Sentinel -. 取消與清理 .-> VFS_Engine
    GC_Sentinel --> DB
    GC_Sentinel --> Disk

    %% 底層持久化
    Auth_Core --> DB
    Session_Mgr --> DB
    VFS_Engine --> DB
    Chunk_Mgr -- 暫存碎片與合併 --> Disk
    VFS_Engine -- 實體同步 --> Disk
    end
```


## 目前進度

### Phase 1: 基礎建設與安全驗證 [已完成 100%]

- [x] **專案骨架與容器化**: 建立 FastAPI 目錄結構、`.env` 管理與 `docker-compose.yml`，cloudflare 留到後期。
- [x] **資料庫基礎與 WAL 配置**: 實作 SQLAlchemy 異步連線，並強制開啟 SQLite **WAL 模式**，定義 `User` 模型。
- [x] **密碼哈希 (Argon2 Hasher)**: 整合 `passlib[argon2]`，實作密碼雜湊與驗證，建立首位 Admin 腳本。
- [x]  **雙重驗證鎖 (TOTP Logic)**: 使用 `pyotp` 實作 2FA 密鑰生成與 6 位數驗證碼。
- [x] **通行證與 IP 紀錄 (JWT & Middleware)**:  實作 JWT 簽發、**CF-Connecting-IP** 識別中介層與基礎限流防護。
- [x] **門禁櫃台 API (Auth Endpoints)**: 串連上述邏輯，完成 `/login`、`/verify-2fa` 與 `/me` 測試端點。

---

### Phase 2: VFS 結構與瀏覽邏輯 (Metadata & Navigation) [已完成 100%]
- [x] **Step 2.1: 元數據建模 (Metadata Schema)**: 建立 `Folder` 與 `File` 模型，包含 UUID, `hash_sha256` 與複合索引優化。
- [x] **Step 2.2: 導航核心 (Navigation Core)**: 實作「UUID 查詢」邏輯與「麵包屑 (Breadcrumbs) 產生器」。
- [x] **Step 2.3: 瀏覽端點 (Browse API)**: 實作 `/browse/ls/{folder_id}` 與 `/browse/search` 端點，支援分頁與排序。
- [x] **Step 2.4: 系統初始化與安全 (Initial Root & Security)**: 實作啟動時自動建立使用者根目錄，並確保 UUID 存取安全性。

### Phase 3: VFS 節點邏輯管理 (Purely Virtual Mutation) [已完成 100%]
> [!NOTE]
> **本階段目標**：專注於純邏輯的「目錄樹節點」維護。在此架構下，目錄僅為資料庫中的虛擬節點，不與磁碟實體資料夾掛鉤。

- [x] **Step 3.0: 基礎優化與安全強化**: 統一 Service 層參數風格，實作 2FA Token 階段鎖定與 User Schema。
- [x] **Step 3.1: 虛擬節點建立 (Mkdir)**：實作具備同級命名衝突檢查的目錄建立。
- [x] **Step 3.2: 節點更名與搬移 (Rename/Move)**：實作防循環引用的目錄/檔案搬移邏輯。
- [x] **Step 3.3: 邏輯刪除與回收站 (Soft Delete)**：實作遞迴邏輯刪除與根目錄保護機制。

### Phase 4: 實體傳輸與檔案管理 (Physical Storage & File VFS)
> [!IMPORTANT]
> **設計準則：實體優先 (Physical-First)**
> 檔案在 VFS 中的「入籍」必須發生在實體儲存成功之後，確保 DB 紀錄與磁碟狀態絕對一致。

- [x] **Step 4.1: 檔案系統功能模組 (Filesystem Infrastructure)** [已完成 100%]
    - **`app/filesystem/chunks.py`** (暫存與合併)：
        - 職責：管理分塊暫存、流式合併與增量雜湊計算。
        - 核心函式：`save_chunk()`, `merge_chunks()`, `cleanup_temp()`。
    - **`app/filesystem/storage.py`** (實體存儲)：
        - 職責：管理正式區實體檔案、刪除與路徑檢索。
        - 核心函式：`delete_file()`, `get_full_path()`。
- [x] **Step 4.2: 持久化模型 (Upload Session)** [已完成 100%]
    - 建立 `UploadSession` 模型，綁定 `owner_id` 與 `target_folder_id`。
    - 職責：追蹤分塊總數、預期雜湊值與會話有效性。
- [x] **Step 4.3: 檔案入籍工作流 (VFS Service Flow)** [已完成 100%]
    - **`VFSService` 核心擴充**：
        - `init_upload()`：驗證權限並啟動會話，實作 **「同名現存檔案」與「活躍上傳會話」的雙重前置衝突防禦**。
        - `upload_chunk()`：處理二進制流寫入。
        - `finalize_upload()`：執行結算（合併 -> 雜湊校驗 -> 建立 File 節點）。
    - **路由層與 API 實作**：註冊三階段 API 端點，並修復了欄位命名不一致導致的 `ResponseValidationError` 回應校驗錯誤。
- [/] **Step 4.4: 串流下載與清理 (IO & Cleanup)** [進行中]
    - [x] **高效下載管道 (包含 ETag 整合)**：實作帶安全 ETag 快取校驗與 Range 續傳支援的 `FileResponse` 流式下載端點。
    - [ ] **上傳進度探測 API**：提供 `GET /vfs/upload/status/{upload_id}`，允許前端在斷線重連後探測伺服器已收到的分塊，跳過重複傳輸。
    - [ ] **主動取消 API**：提供 `POST /vfs/upload/cancel`，允許前端主動發起取消以即時清理會話紀錄與暫存碎片檔案。
    - [ ] **定時背景哨兵 (GC)**：於服務啟動時掛載背景協程，定時物理清除資料庫中過期（>24小時）的活躍會話，並清除對應的磁碟暫存。

### Phase 5: 系統完善與管理 (Admin & Polish)
- [ ] **Step 5.1: 自助安全管理 (2FA 綁定與註冊流程)**：
    * **現存問題分析**：目前 `/login` 端點無條件回傳 `require_2fa: true`，且在 `/verify-2fa` 中直接利用 `otp.verify_otp_code` 校驗尚未產生的 2FA 安全金鑰（新使用者初始為 `None`），這將導致未啟用 2FA 的新註冊使用者根本無法登入。同時系統中也缺乏註冊與綁定 2FA 的 API。
    * **預期業務流程**：使用者註冊 $\rightarrow$ 登入（此時未啟用 2FA，免輸入 OTP 驗證碼） $\rightarrow$ 進入控制台 $\rightarrow$ 請求產生 2FA 金鑰與 QR Code $\rightarrow$ 輸入手機 OTP 首次驗證 $\rightarrow$ 正式啟用 2FA 保護。
    * **具體待辦步驟**：
      - [ ] **1. 使用者註冊端點**：新增 `POST /api/auth/register` API，新註冊使用者之 `is_totp_enabled` 預設為 `False`，`totp_secret` 為 `None`。
      - [ ] **2. 登入邏輯重構**：重構 `POST /api/auth/login` 的驗證邏輯。若使用者 `is_totp_enabled` 為 `False`，直接簽發正式的 JWT `access_token`；若為 `True`，才簽發短效 `two_fa_token` 並回傳 `require_2fa: true`。
      - [ ] **3. 2FA 兩階段綁定端點**：
        - [ ] 新增 `POST /api/auth/2fa/generate`：產生隨機 Base32 金鑰並暫存於資料庫（此時 `is_totp_enabled` 仍保持 `False`，避免掃碼前被鎖定），回傳金鑰與 QR Code 連結。
        - [ ] 新增 `POST /api/auth/2fa/enable`：驗證使用者輸入的手機 App OTP 驗證碼，成功後更新 `is_totp_enabled` 為 `True`。
      - [ ] **4. 2FA 停用端點**：新增 `POST /api/auth/2fa/disable`，校驗當前 OTP 驗證碼後將 `is_totp_enabled` 設為 `False` 並清除安全金鑰。
      - [ ] **5. Schema 與測試腳本更新**：修改 `LoginResponse` 結構以支援直接回傳 `access_token` 與 `token_type`；更新 `test_api.py` 測試腳本，支援非強制 2FA 情況下的登入與綁定流程測試。
- [ ] **待定**: 根據實測反饋決定後續系統優化項目。

### Phase 6: 輔助系統與處理 (功能增強)
- [ ] **Media Processor**: 實作非同步媒體處理器，生成縮圖與提取元數據。


## 技術棧
- **Backend**: FastAPI (Python)
- **Frontend**: Vue 3 + Vite + Tailwind CSS
- **Database**: SQLAlchemy 2.0 (Async) + SQLite
- **Security**: OAuth2 (Bearer Token), Argon2 (Password), PyOTP (2FA), Jose (JWT)
- **Container**: Docker + Docker Compose

## 快速啟動 (開發環境)
```powershell
docker-compose up --build -d
```
服務啟動後可訪問：
- **API 文件**: `http://localhost:8000/docs`
- **前端介面**: `http://localhost:5173` (開發中)

---

## 架構設計思考 (Architectural Thinking)

### 1. 異常處理的層級分工 (Exception Handling)
**問題**：`HTTPException` 應該在 Service Layer 還是 API Layer 處理？
**原則**：**「低層拋出訊息，高層決定行為」**。
- **Service Layer (底層/廚師)**：負責偵測「業務邏輯錯誤」（如：找不到節點、命名衝突）。它應該拋出 **純粹的邏輯異常** (如 `NodeNotFoundError`)，而不是 HTTP 異常。
- **API Layer (高層/服務生)**：負責將邏輯異常 **「翻譯」** 成適合當前通訊協定的格式（如 `HTTP 404`）。
- **優點**：確保 Service Layer 的通用性，使其能被 CLI、腳本或背景任務複用，而不依賴於特定的 Web 框架 (FastAPI)。

### 2. Fail-Fast 原則
- **偵測 (Detection)**：錯誤偵測應離「成因」與「實作地點」越近越好，以便於快速定位問題。
- **處理 (Handling)**：錯誤處置應拉遠到高層決定，以保持系統整體的彈性與策略一致性。

### 3. 垃圾回收 (GC) 的解耦與非同步執行緒設計
**問題 1：AnyIO 執行緒池混用協程 Bug**
- **狀況**：在舊版垃圾回收設計中，錯誤地將一個 `async def` 協程函式傳入了 `anyio.to_thread.run_sync()`。
- **成因**：`run_sync` 本身是為了將「同步阻塞操作 (如本機磁碟 I/O)」移至背景執行緒池執行，以防止卡死 Event Loop。當傳入 `async def` 時，背景執行緒在沒有 Event Loop 調度的情況下直接呼叫它，只會瞬間得到一個 `<coroutine>` 物件，而根本不會執行其內部的實體硬碟檢查。該物件在 Python 的 Boolean 判定中永遠為 `True`，導致過期會話防護機制徹底失效。
- **解法**：將原生同步的磁碟操作（例如內建的 `os.path.exists`）作為參數直接傳入 `run_sync` 第一個位置，使其在背景執行緒中安全執行；而我們自己寫的非同步業務（`async def`）則直接在主執行緒中用 `await` 呼叫。

**問題 2：同級服務互相依賴 (Sibling Coupling) 與循環導入**
- **狀況**：若將垃圾回收業務獨立為 `GCService` 放在 `services/` 資料夾中，因為它需要調用 `VFSService` 來取消上傳會話，這使得兩個同層級的 Service 產生了緊密耦合，在 Python 中極易引發 **循環導入 (Circular Import)**。
- **解法**：將垃圾回收定位為與 API 同等地位的 **「入口驅動層 (Entry Layer)」**，並在 `app/gc/` 資料夾下建立獨立的 `sentinel.py` 模組。由 `gc/sentinel.py` 向下單向導入資料庫與 `VFSService` 並呼叫 `cancel_upload()`。如此實現了**嚴格的單向依賴 (Unidirectional Dependency)**，既重用了核心上傳取消邏輯，又讓 `vfs_service.py` 保持 100% 的純粹與職責單一。

