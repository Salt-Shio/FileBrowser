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

    subgraph Layer_3_File [4. 檔案協調引擎]
        VFS[虛擬目錄: 路徑與結構管理]
        Chunk_Mgr[分片處理: 緩存與合併]
        Tx_Coord[事務協調: DB/Disk 同步]
        
        Chunk_Mgr --> Tx_Coord
        Tx_Coord --> VFS
    end

    %% 第四層：數據持久化
    subgraph Layer_4 [5. 數據持久層]
        DB[(SQLite: Metadata / 使用者)]
        Disk[實體磁碟: 二進制檔案]
    end

    %% 跨層對接邏輯 (合併與獨立處理)
    EP_Login --> Auth_Core
    EP_2FA --> Auth_Core
    
    %% 查詢類：對接 VFS
    EP_Browse --> VFS
    
    %% 傳輸類：對接 Uploader 或 Disk
    EP_Upload --> Chunk_Mgr
    EP_Download --> VFS
    
    %% 變更類：對接 Tx_Coord (實體同步)
    EP_Modify --> Tx_Coord
    EP_Mkdir --> Tx_Coord
    EP_Delete --> Tx_Coord

    %% 底層持久化
    Auth_Core --> DB
    Session_Mgr --> DB
    Tx_Coord --> Disk
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

### Phase 2: VFS 結構與瀏覽邏輯 (檔案結構)
*   **對應模組**：EP_Browse -> VFS -> DB (File Metadata)
*   **實作重點**：
    *   定義檔案元數據 (Metadata) 模型。
    *   實作虛擬目錄解析邏輯 (將 DB 記錄映射至邏輯目錄樹)。
    *   完成「讀取列表」與「搜尋檔案」功能。

### Phase 3: 事務協調與實體同步 (變更管理)
*   **對應模組**：EP_Modify/Mkdir/Delete -> Tx_Coord -> VFS/Disk
*   **實作重點**：
    *   實作 **Tx_Coord (事務協調器)**，處理磁碟 `os.rename/mkdir` 與資料庫記錄的同步原子性。
    *   完成「建立資料夾」、「移動位置」與「重命名」功能。
    *   完成「檔案刪除」功能（包含實體與記錄的同步清理）。

### Phase 4: 數據傳輸管道 (檔案 IO)
*   **對應模組**：EP_Upload/Download -> Chunk_Mgr -> Tx_Coord -> Disk
*   **實作重點**：
    *   實作 **Chunk_Mgr (分片處理器)** 處理大檔案上傳、暫存與合併。
    *   實作檔案串流讀取 (Download) 與寫入 (Upload) 的 IO 優化。

### Phase 5: 輔助系統與處理 (功能增強)
*   **對應模組**：Media_Aux
*   **實作重點**：
    *   實作非同步媒體處理器 (Media Processor)，生成縮圖與提取元數據。

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