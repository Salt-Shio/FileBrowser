# 個人檔案分享系統 - 系統化架構說明書

本文件詳述了系統的邏輯功能解耦設計，強調「功能模組化」與「事務完整性」，確保個人檔案存取的高度安全與穩定。

---

## 1. 邏輯功能架構圖 (Pipeline Architecture)

此圖表展示了從使用者請求進入，到具體功能分發，最後執行底層邏輯與持久化的完整管道。

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

---

## 2. 實作順序規劃 (Implementation Roadmap)

根據上述 Pipeline 架構，系統將分為五個階段進行開發，確保每一層的依賴關係正確且風險受控：

### Phase 1: 基礎設施與 IAM 安全核心 (容器化與身分驗證)
*   **對應模組**：CF_Tunnel -> Ingress -> Auth_Endpoints -> IAM_Core -> DB (User)
*   **詳細實作步驟**：
    *   **Step 1.1: 專案骨架與容器化 (Project Scaffold)**
        *   建立 FastAPI 目錄結構、`.env` 管理與 `docker-compose.yml` (含 cloudflared 佔位)。
    *   **Step 1.2: 資料庫基礎與 WAL 配置 (Database Foundation)**
        *   實作 SQLAlchemy 異步連線，並強制開啟 SQLite **WAL 模式**，定義 `User` 模型。
    *   **Step 1.3: 密碼碎紙機 (Argon2 Hasher)**
        *   整合 `passlib[argon2]`，實作密碼雜湊與驗證，建立首位 Admin 腳本。
    *   **Step 1.4: 雙重驗證鎖 (TOTP Logic)**
        *   使用 `pyotp` 實作 2FA 密鑰生成與 6 位數驗證邏輯。
    *   **Step 1.5: 通行證與警衛 (JWT & Middleware)**
        *   實作 JWT 簽發、**CF-Connecting-IP** 識別中介層與基礎限流防護。
    *   **Step 1.6: 門禁櫃台 API (Auth Endpoints)**
        *   串連上述邏輯，完成 `/login`、`/verify-2fa` 與 `/me` 測試端點。

### Phase 2: VFS 結構與瀏覽邏輯 (Metadata & Navigation)
*   **對應模組**：EP_Browse -> VFS_Engine -> DB
*   **詳細實作步驟**：
    *   **Step 2.1: 元數據建模 (Metadata Schema)**
        *   建立 `Folder` 與 `File` 的 SQLAlchemy 模型，包含 UUID, `hash_sha256` 與複合索引優化。
    *   **Step 2.2: 導航核心 (Navigation Core)**
        *   實作「UUID 查詢」邏輯與「麵包屑 (Breadcrumbs) 產生器」，為前端導航提供結構。
    *   **Step 2.3: 瀏覽端點 (Browse API)**
        *   實作 `/browse/ls/{folder_id}` 與 `/browse/search` 端點，支援分頁、排序與 Pydantic Schema。
    *   **Step 2.4: 系統初始化與安全 (Initial Root & Security)**
        *   實作啟動時自動建立使用者根目錄，並確保所有 UUID 存取皆通過 `owner_id` 檢查。

### Phase 3: VFS 變更管理 (Mutation & Sync)
*   **對應模組**：EP_Modify/Mkdir/Delete -> VFS_Engine -> DB/Disk
*   **詳細實作步驟**：
    *   **Step 3.1: 事務同步封裝 (Sync Wrapper)**
        *   實作 VFS 核心內部用於確保 DB 紀錄與磁碟實體「雙寫一致性」的同步邏輯。
    *   **Step 3.2: 目錄管理 (Mkdir/Rename)**
        *   實現資料夾建立與檔案/資料夾的重命名邏輯。
    *   **Step 3.3: 虛擬搬移 (Move)**
        *   實作秒級搬移邏輯 (僅修改 `parent_id`)，並處理目標路徑衝突檢查。
    *   **Step 3.4: 安全刪除 (Delete)**
        *   實作刪除標記與實體檔案的同步清理機制。

### Phase 4: 傳輸管道 (Chunked IO)
*   **對應模組**：EP_Upload/Download -> Chunk_Mgr -> VFS_Engine -> Disk
*   **詳細實作步驟**：
    *   **Step 4.1: 分片管理 (Chunk_Mgr)**
        *   實作後端分片接收邏輯，並暫存於磁碟臨時區 (`/temp/chunks`)。
    *   **Step 4.2: 合併與註冊 (Merge & Register)**
        *   完成分片拼接、雜湊 (SHA256) 校驗，並向 VFS 引擎登記正式 Metadata。
    *   **Step 4.3: 串流下載 (Streaming)**
        *   實作基於 FastAPI `FileResponse` 的串流下載管道，優化大檔案讀取性能。
    *   **Step 4.4: 碎片垃圾回收 (GC)**
        *   實作背景清理機制，自動回收超過 24 小時未完成的孤兒分片。

### Phase 5: 輔助系統與處理 (功能增強)
*   **對應模組**：Media_Aux
*   **實作重點**：
    *   實作非同步媒體處理器 (Media Processor)，生成縮圖與提取元數據。

---

## 3. 實作注意事項 (Critical Implementation Notes)

在實作各階段模組時，必須嚴格遵守以下準則，以確保系統的健壯性：

### 1. SQLite 併發效能優化 (Phase 1 & 3)
*   **問題**：分片上傳與大量檔案操作可能導致 `Database is locked`。
*   **準則**：初始化資料庫連線時，必須開啟 **WAL (Write-Ahead Logging)** 模式。這能讓讀寫操作在很大程度上互不阻塞，大幅提升併發能力。

### 2. 跨系統事務一致性 (Phase 3)
*   **問題**：Disk 與 DB 是獨立系統，難以實現硬性原子性。
*   **準則 (雙寫邏輯)**：
    *   **建立/上傳**：採「磁碟優先」。
        1. 寫入實體磁碟。
        2. 成功後更新 DB Metadata。
        3. 若 DB 失敗，立即執行磁碟回滾（刪除已寫檔案）。
    *   **刪除/移動**：採「標記優先」。
        1. 在 DB 中將記錄標記為 `pending_action` 或軟刪除。
        2. 執行磁碟實體操作（`os.remove`/`os.rename`）。
        3. 成功後，再徹底完成 DB 狀態更新或清除記錄。

### 3. 資源清理與回收 (Phase 4)
*   **問題**：中斷的上傳會產生「孤兒分片 (Orphan Chunks)」佔據空間。
*   **準則**：`Chunk_Mgr` 必須具備垃圾回收機制。需實作背景排程或定期檢查，自動刪除超過 24 小時未完成合併的過時分片目錄。
