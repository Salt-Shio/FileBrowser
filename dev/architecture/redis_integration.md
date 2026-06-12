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

## 5. 未來優化規劃 (Future Optimizations)

引入 Redis 後，專案已具備優異的快取能力。
已規劃將「虛擬目錄架構快取」列入長期的優化項目（詳見 `docs/TODO.md`），以降低頻繁讀取目錄樹時所造成的 SQLite I/O 開銷。
