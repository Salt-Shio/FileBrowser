# File Explorer

一個用來做檔案上傳的個人網站，方便自己遠端操作

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

    %% 第三層：核心業務引擎 (Engines)
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

    %% 第四層：數據持久化
    subgraph Layer_4 [5. 數據持久層]
        DB[(SQLite: Metadata / 使用者)]
        Disk[實體磁碟: 二進制檔案]
    end

    %% 跨層對接邏輯
    EP_Login --> Auth_Core
    EP_2FA --> Auth_Core
    
    %% 檔案操作：統一對接 VFS 引擎
    EP_Browse --> VFS_Engine
    EP_Download --> VFS_Engine
    EP_Upload --> VFS_Engine
    EP_Modify --> VFS_Engine
    EP_Mkdir --> VFS_Engine
    EP_Delete --> VFS_Engine

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

### Phase 3: VFS 目錄樹管理 (Folder Management)
> [!NOTE]
> **本階段目標**：專注於純邏輯的「目錄結構」維護，不涉及任何實體檔案 IO。

- [ ] **Step 3.0: 基礎優化與 User Schema**: 補齊 `User` 相關 Schema，並將 Service 層風格統一。
- [ ] **Step 3.1: 目錄建立 (Mkdir)**: 實作資料夾建立，包含同名檢查與權限驗證。
- [ ] **Step 3.2: 目錄變更 (Folder Rename/Move)**: 僅針對「資料夾」進行重新命名與路徑搬移。
- [ ] **Step 3.3: 目錄邏輯刪除 (Folder Logical Delete)**: 實現資料夾的 `is_deleted` 標記機制。

### Phase 4: 實體傳輸與檔案管理 (Physical Storage & File VFS)
> [!IMPORTANT]
> **設計準則：實體優先 (Physical-First)**
> 檔案在 VFS 中的「入籍」必須發生在實體儲存成功之後，確保 DB 紀錄與磁碟狀態絕對一致。

- [ ] **Step 4.1: 儲存抽象層 (Storage Provider)**: 實作底層硬碟讀寫引擎，處理 UUID 檔名與實體路徑映射。
- [ ] **Step 4.2: 檔案入籍與變更 (File VFS Mutation)**: 實作「檔案」的建立、重新命名、搬移與邏輯刪除邏輯。
- [ ] **Step 4.3: 分片傳輸管道 (Chunked Upload)**: 實作分片接收、雜湊校驗與背景合併機制。
- [ ] **Step 4.4: 串流下載與清理 (IO & Cleanup)**: 實作高性能下載管道，以及根據 `is_deleted` 狀態執行的實體清理。

### Phase 5: 輔助系統與處理 (功能增強)
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