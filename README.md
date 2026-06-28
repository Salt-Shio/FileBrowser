# File Explorer

這個專案主要是給我個人學習與使用的，類似一個 NAS 系統架設在小電腦上，但是我希望把它做成支援多人的檔案系統

## 前端展示

<video width="100%" controls>
  <source src="./docs/salty-file-explore-demo.mp4" type="video/mp4">
</video>

## 使用到的技術

* 後端 (Python)
    * FastAPI (非同步核心框架)
    * SQLAlchemy (非同步 ORM)
    * SQLite (開啟 WAL 模式的高效本地資料庫)
    * Redis (快取、限流與單次下載憑證鎖)
    * PyOTP & JWT (雙重驗證 2FA 與身分授權)
* 前端 (TypeScript)
    * Vue 3 (Composition API)
    * Vite (極速建置工具)
    * Pinia (狀態管理)
    * Tailwind CSS (玻璃擬物化 Glassmorphism 設計)
    * Axios (支援攔截器與上傳進度追蹤)
* Infra (基礎設施)
    * Docker & Docker Compose (容器化微服務部署)
    * Tailscale (Zero-Trust P2P 虛擬區域網路)
    * Nginx Proxy Manager (反向代理與 Let's Encrypt 自動憑證)
    * Cloudflare (DNS 解析管理)

## 系統核心特色 (Key Features)

### 📂 虛擬檔案系統 (Virtual File System, VFS)
* **資料庫驅動 (Metadata)**：檔案改名與搬移皆為純資料庫操作，零磁碟 I/O 延遲。
* **併發分塊與隨機寫入**：大檔案前端切塊併發上傳，後端預分配 Sparse File 空間並透過 `seek(offset)` 隨機寫入，徹底消滅大檔案合併瓶頸。
* **跨資料夾斷點續傳**：無縫暫停與恢復傳輸，即使切換不同資料夾也能記住進度並正確歸檔。
* **軟刪除與背景清理 (GC)**：檔案刪除先進入隱藏狀態，由背景哨兵 (Sentinel) 定時非同步清理實體磁碟。

### 🛡️ 資安與身分驗證 (Security & Auth)
* **JWT 授權 & Argon2 加密**：採用高強度密碼學防護與無狀態授權。
* **雙重驗證 (2FA/TOTP)**：支援 Authenticator App 掃碼綁定，防止帳號盜用。
* **單次下載憑證 (Ticket)**：透過 Redis 派發 30 秒拋棄式下載憑證，防禦重放攻擊與伺服器過載。

## 業務功能架構圖 (Functional Architecture)

本圖表呈現了外部請求從進入系統到觸發底層實體寫入的「功能端點與業務流向」。

```mermaid
%%{init: {'themeVariables': { 'fontSize': '18px'}}}%%
graph TD
    %% 外部請求流向
    User([個人使用者]) -- HTTPS (Tailscale/公網) --> NPM[Nginx Proxy Manager]
    
    subgraph Docker_Boundary [Docker 部署邊界]
        NPM -- Proxy Pass --> Ingress
        
        subgraph Layer_1 [1. 流量閘道層]
            Ingress[Web Nginx / FastAPI 攔截器]
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
        Chunk_Mgr[Chunk_Mgr: 隨機寫入 Sparse File]
        
        %% 內部邏輯流
        VFS_Engine -. 權限驗證 .-> Chunk_Mgr
        Chunk_Mgr -- 結算完成 --> VFS_Engine
    end

    subgraph Layer_3_GC [背景維護核心]
        GC_Sentinel[背景 GC 哨兵: 定期大掃除]
    end

    %% 第四層：數據持久化與快取
    subgraph Layer_4 [5. 數據持久層與快取]
        DB[(SQLite: Metadata / 使用者)]
        Disk[實體磁碟: 二進制檔案]
        RedisCache[(Redis: 臨時憑證 / 快取 / 限流)]
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
    GC_Sentinel --> DB
    GC_Sentinel --> Disk
    GC_Sentinel --> RedisCache

    %% 底層持久化
    Auth_Core --> DB
    Session_Mgr --> DB
    VFS_Engine --> DB
    VFS_Engine --> RedisCache
    Chunk_Mgr -- 隨機寫入 --> Disk
    VFS_Engine -- 實體同步 --> Disk
    end
```

---

## 系統程式結構圖 (System Module Structure)

本圖表呈現以後端 `app.main` 為核心的「程式碼調用階層與模組依賴關係」。

```mermaid
%%{init: {'themeVariables': { 'fontSize': '20px'}}}%%
graph TD
    subgraph Layer_1 [管理層 - 入口]
        MAIN["main.py (入口點)"]
        MIDDLEWARE["middleware/ (攔截器)"]
        CORE["core/config.py (系統配置)"]
        API_INIT["api/__init__.py (總路由)"]
        GC_SENTINEL["gc/sentinel.py (垃圾回收哨兵)"]
    end

    subgraph Layer_2 [介面層 - Router]
        VFS_API["api/vfs.py (檔案系統)"]
        AUTH_API["api/auth.py (身分驗證)"]
    end

    subgraph Layer_3 [執行層 - Service & Deps]
        DEPS["api/deps.py (依賴注入中心)"]
        VFS_SVC["services/vfs_service.py (檔案業務)"]
        AUTH_SVC["services/auth_service.py (身分業務)"]
    end

    subgraph Layer_4 [基礎層 - Security, Data & Storage]
        DB[("database.py / DB")]
        REDIS[("core/cache.py / Redis")]
        FILESYSTEM["filesystem/ (實體存儲策略)"]
        MODELS["models/ (資料結構)"]
        SCHEMAS["schemas/ (Pydantic)"]
        JWT["security/jwt.py"]
        HASHER["security/hasher.py"]
        OTP["security/otp.py"]
    end

    %% 調用關係
    MAIN --> MIDDLEWARE
    MAIN --> CORE
    MAIN --> API_INIT
    MAIN --> GC_SENTINEL
    MAIN -.->|Lifespan Init| DB
    MAIN -.->|Lifespan Init| REDIS

    API_INIT --> VFS_API
    API_INIT --> AUTH_API

    %% 業務與依賴 (DI 注入流程)
    VFS_API --> DEPS
    AUTH_API --> DEPS
    DEPS -.->|Instantiate| VFS_SVC
    DEPS -.->|Instantiate| AUTH_SVC

    %% 執行層調用基礎層 (由 DEPS 組裝注入)
    DEPS --> DB
    DEPS --> REDIS
    DEPS --> FILESYSTEM

    VFS_SVC --> MODELS
    VFS_SVC --> JWT

    AUTH_SVC --> MODELS
    AUTH_SVC --> JWT
    AUTH_SVC --> HASHER
    AUTH_SVC --> OTP

    %% 背景 GC 哨兵調用
    GC_SENTINEL --> DB
    GC_SENTINEL --> FILESYSTEM

    %% Schema 調用
    VFS_API -.-> SCHEMAS
    AUTH_API -.-> SCHEMAS

    %% 樣式美化
    style MAIN fill:#FF9800,stroke:#333,stroke-width:4px,color:#000
    style GC_SENTINEL fill:#FF9800,stroke:#333,stroke-width:2px,color:#000
    style API_INIT fill:#2196F3,stroke:#333,stroke-width:2px,color:#fff
    style DEPS fill:#E1BEE7,stroke:#333,stroke-width:2px,color:#000
    style AUTH_SVC fill:#C8E6C9,stroke:#333,stroke-width:2px,color:#000
    style VFS_SVC fill:#C8E6C9,stroke:#333,stroke-width:2px,color:#000
    style DB fill:#ECEFF1,stroke:#333,color:#000
    style FILESYSTEM fill:#FFF9C4,stroke:#333,color:#000
```

### 核心層級說明

1.  **管理層 (Top)**：`main.py` 負責將所有模組組裝起來。在應用啟動時，它會拉起背景垃圾回收哨兵 (`app/gc/sentinel.py`) 任務並初始化資料庫與 Redis 連線池 (`lifespan`)；並在應用關閉時，優雅地釋放連線與取消哨兵，避免資源洩漏。
2.  **路由層 (Router)**：`api/` 負責分流外部 HTTP 請求，但不處理複雜邏輯。
3.  **依賴層 (Deps)**：`deps.py` 像是一個橋樑，把底層的「資料庫」、「Redis 快取」與「安全工具」提供給上層。
4.  **執行層 (Logic)**：`services/` 才是真正動手處理資料的地方。
5.  **基礎層 (Base)**：`models`, `database`, `cache.py`, `security` 是最純粹的工具，不依賴任何人。
