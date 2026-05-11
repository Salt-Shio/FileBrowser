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

### Phase 2: VFS 結構與瀏覽邏輯 (Metadata & Navigation)
- [x] **Step 2.1: 元數據建模 (Metadata Schema)**: 建立 `Folder` 與 `File` 模型，包含 UUID, `hash_sha256` 與複合索引優化。
- [x] **Step 2.2: 導航核心 (Navigation Core)**: 實作「UUID 查詢」邏輯與「麵包屑 (Breadcrumbs) 產生器」。
- [ ] **Step 2.3: 瀏覽端點 (Browse API)**: 實作 `/browse/ls/{folder_id}` 與 `/browse/search` 端點，支援分頁與排序。
- [ ] **Step 2.4: 系統初始化與安全 (Initial Root & Security)**: 實作啟動時自動建立使用者根目錄，並確保 UUID 存取安全性。

### Phase 3: VFS 變更管理 (Mutation & Sync)
- [ ] **Step 3.1: 事務同步封裝 (Sync Wrapper)**: 實作確保 DB 紀錄與磁碟實體「雙寫一致性」的核心同步邏輯。
- [ ] **Step 3.2: 目錄管理 (Mkdir/Rename)**: 實現資料夾建立與檔案/資料夾的重命名邏輯。
- [ ] **Step 3.3: 虛擬搬移 (Move)**: 實作秒級搬移邏輯 (僅修改 `parent_id`)。
- [ ] **Step 3.4: 安全刪除 (Delete)**: 實作刪除標記與實體檔案的同步清理機制。

### Phase 4: 傳輸管道 (Chunked IO)
- [ ] **Step 4.1: 分片管理 (Chunk_Mgr)**: 實作後端分片接收與磁碟臨時區 (`/temp/chunks`) 管理。
- [ ] **Step 4.2: 檔案合併與註冊 (Merge & Register)**: 完成碎片拼接、雜湊 (SHA256) 校驗與 VFS 登記。
- [ ] **Step 4.3: 串流下載 (Streaming)**: 實作基於 FastAPI `FileResponse` 的高性能串流下載管道。
- [ ] **Step 4.4: 碎片垃圾回收 (GC)**: 實作背景清理機制，自動回收未完成的孤兒分片。

### Phase 5: 輔助系統與處理 (功能增強)
- [ ] **Media Processor**: 實作非同步媒體處理器，生成縮圖與提取元數據。

## 技術棧
- **Backend**: FastAPI (Python)
- **Frontend**: Vue 3 + Vite + Tailwind CSS
- **Database**: SQLAlchemy 2.0 (Async) + SQLite
- **Security**: Argon2 (Password), PyOTP (2FA), Jose (JWT)
- **Container**: Docker + Docker Compose

## 快速啟動 (開發環境)
```powershell
docker-compose up --build -d
```
服務啟動後可訪問：
- **API 文件**: `http://localhost:8000/docs`
- **前端介面**: `http://localhost:5173` (開發中)