# Redis 系統整合架構設計 (定案)

本文檔作為引入 Redis 至專案基礎設施的正式設計規範。所有牽涉到 Redis 操作與開發的流程，均須遵循以下約定。

## 1. 基礎連線與生命週期 (Connection & Lifespan)

*   **套件選擇**：使用官方 `redis` 套件的非同步介面 (`redis.asyncio`)，符合專案 `async_concurrency_guide.md` 的非同步規範。
*   **連線池管理**：
    *   模組統一命名為 `app/core/cache.py`。
    *   預設連線池大小設定為 `max_connections=20`，對於單一 FastAPI Worker 已非常充裕。
*   **生命週期**：由 `main.py` 的 FastAPI `lifespan` 統一管理啟動與關閉。
*   **依賴注入**：在 `api/deps.py` 新增 `get_redis`，維持單向依賴原則 (`Routers -> Deps -> Infrastructure`)。

---

## 2. 鍵值命名規範 (Key Naming Convention)

為避免不同功能（如下載憑證、併發鎖、快取）之間的 Key 衝突，全域統一採用以下結構進行命名：

*   **格式約定**：`{模組}:{功能}:{ID}`
    *   *範例（下載 Ticket）*：`vfs:ticket:download:<uuid>`
    *   *範例（分塊上傳鎖）*：`vfs:lock:upload:<upload_id>`
*   **資料結構**：除非單純的字串（如 Ticket ID 映射到 File ID），否則複雜物件一律使用 JSON 序列化儲存。

---

## 3. 本機開發環境政策 (Local Development)

本專案將 Redis 視為**一級基礎設施 (First-class Infrastructure)**。

*   **強依賴機制 (Fail-fast)**：無論是開發或正式環境，**必須有 Redis**。若 FastAPI 啟動時無法與 Redis 建立連線，將直接 Crash (Fail-fast)，拒絕啟動。此舉確保本地開發與正式生產環境的絕對一致性。
*   **開發者要求**：本機開發時，必須使用 `docker-compose up` 啟動包含 Redis 在內的基礎設施環境。

---

## 4. 例外處理與容錯機制 (Exception Management)

*   **連線超時設定 (Timeout)**：設定極短的 Socket Timeout（例如 `socket_timeout=2` 秒），防止 Redis 塞車時引發骨牌效應導致整台 API Server 卡死。
*   **強依賴場景中斷**：針對下載 Ticket 等強依賴 Redis 的功能，若連線失敗將直接拋出 `500 Internal Server Error` 終止請求。

---

## 5. 大檔案下載 Ticket 憑證與連線限制機制 (定案)

本機制用於解決大檔案下載重複點擊導致後端效能超載（起飛）問題，改以單次臨時 Ticket 憑證接管下載流，並實作連線次數限制與狀態監控。

### 5.1 Redis 狀態規劃與生命週期

*   **Ticket 憑證鍵 (`vfs:ticket:download:{ticket_uuid}`)**：
    *   **存放資訊**：JSON 序列化儲存 `file_id` 與 `owner_id`。
    *   **生命週期**：TTL 固定 **30 秒**，由 Redis 自動過期消亡，中途絕不提前刪除。
*   **使用者防刷鎖 (`vfs:ticket:user_download:{owner_id}:{file_id}`)**：
    *   **存放資訊**：指向當前的 Ticket UUID。
    *   **生命週期**：TTL 固定 **30 秒**，防範使用者在 30 秒內重複點擊下載生成多個 Ticket。
*   **連線次數計數器 (`vfs:ticket:active_conns:{ticket_uuid}`)**：
    *   **計數機制**：每次下載連入時原子 `INCR` 累加。第一個連線建立時設定 TTL **30 秒**，最大連線上限限制為 **4**（以支援多執行緒斷點續傳）。即使達到上限亦不手動刪除 Ticket，固定等 30 秒自動消亡。

### 5.2 過期與清理原則 (無狀態解耦)

*   **不進行手動遞減或刪除**：不要在連線結束的 `finally` 區塊中進行 `DECR` 或 `delete` 操作。
*   **設計考量**：大檔案傳輸中斷時，ASGI 協程可能已被取消，在此混沌狀態下執行非同步 Redis I/O 容易引發逾時、連線 Socket 異常或因操作失敗導致的數值殘留。所有計數器與鎖狀態清理，完全交由 Redis TTL 自動清理，達成高穩定的無狀態化設計。

---

## 6. 現有 Redis 資料庫鍵值清單 (Current Data Schema)

截至目前，系統在 Redis 中儲存了以下三大類核心狀態與快取資料，均嚴格遵守無狀態設計與 TTL 自動消亡原則：

### 6.1 大檔案下載與限流 (Download Tickets)
*   **`vfs:ticket:download:{ticket_uuid}`**：
    *   **用途**：大檔案單次下載憑證，存放 `{file_id, owner_id}` 等授權資訊。
    *   **生命週期**：TTL 固定 **30 秒**。
*   **`vfs:ticket:user_download:{owner_id}:{file_id}`**：
    *   **用途**：防刷鎖，防止同一使用者 30 秒內對同一檔案狂刷下載鈕產生大量重複 Ticket。
    *   **生命週期**：TTL 固定 **30 秒**。
*   **`vfs:ticket:active_conns:{ticket_uuid}`**：
    *   **用途**：記錄單一 Ticket 目前的併發連線數（例如斷點續傳的平行下載）。上限限制為 4，避免頻寬被單一檔案耗盡。
    *   **生命週期**：TTL 固定 **30 秒**。

### 6.2 虛擬檔案目錄快取 (VFS Directory Cache)
*   **`vfs:root:{owner_id}`**：
    *   **用途**：快取使用者的根目錄 (`root`) Folder ID，消滅每次 API 請求都需連線 SQLite 查詢 Root ID 的 I/O 開銷。
    *   **清理機制**：當發生根目錄遺失重建時才會手動更新/刪除。
*   **`vfs:browse:{owner_id}:{folder_id}`**：
    *   **用途**：快取該目錄下所有子資料夾、檔案列表與麵包屑導航資料的 JSON 序列化字串。極大幅提升瀏覽效能。
    *   **清理機制**：當該目錄發生異動（如 `mkdir`, `move`, `rename`, `delete` 或「檔案上傳完成」）時，觸發雙刪機制 (Double Delete) 強制清除該層級與其父層級的快取。

### 6.3 認證與防重放攻擊 (Auth 2FA Replay Protection)
*   **`auth:lock:2fa_replay:{username}:{otp_code}`**：
    *   **用途**：防範 2FA (TOTP) 重放攻擊 (Replay Attack) 的鎖。當使用者成功登入、啟用或停用 2FA 時寫入該代碼，確保同一個 6 位數密碼在視窗內無法被惡意攔截並重用。
    *   **生命週期**：TTL 固定綁定環境變數 `TWO_FA_REPLAY_TTL`（通常為 30 秒內）。
