# 專案實作與 Figma 對齊 TODO 清單

## Phase 5.1: Settings & 2FA 安全管理 [已完成 100%]
- [x] 1. 安裝 `qrcode.vue` 處理 QRCode 生成
- [x] 2. 更新 `src/api/auth.ts`，封裝 `/2fa/generate`, `/2fa/enable`, `/2fa/disable` 等 API。
- [x] 3. 更新 `src/stores/auth.ts`，擴充 2FA 相關操作狀態管理。
- [x] 4. 實作 `src/components/auth/TwoFactorEnableModal.vue` 元件 (依照 Figma UI 設計)。
- [x] 5. 實作 `src/views/SettingsView.vue` 畫面與互動邏輯 (包含表單與呼叫 Modal)。
- [x] 6. 測試完整的 2FA 啟用流程與後續登入驗證，並等待使用者確認完成。

---

## Phase 5.2: 全域導航與頁面麵包屑優化 (結合無色科技感) [已完成 100%]
- [x] 1. 調整 [App.vue](file:///d:/Project/file-explorer/src/App.vue) 中的 Navbar 選單字體比例（對齊 Figma 的大字體風格，標題 `55px`，選單 `45px`）。
- [x] 2. 在全頁頂部加入「`主頁 --> [目前頁面]`」的白色底線麵包屑路徑顯示區（具備科幻網格與等寬字體）。
- [x] 3. 全域字體優化：完整引入並套用 Figma 中指定的 'Inter' 與 'JetBrains Mono' 等寬字體系列，並加上抗鋸齒渲染。

---

## Phase 5.3: 設定頁面修改密碼功能整合 [已完成 100%]
- [x] 1. 後端新增密碼更變與確認之 API 路由與對應 Service。
- [x] 2. 前端 [SettingsView.vue](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/views/SettingsView.vue) 對接後端修改密碼 API，並將「確認」更變的邏輯落實。

---

## Phase 5.4: VFS 第 1 階段 - 基礎佈局與唯讀瀏覽 [已完成 100%]
- [x] 1. 新增前端 VFS API 請求封裝 [vfs.ts](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/api/vfs.ts)，封裝 `/ls` 唯讀端點。
- [x] 2. 新增 Pinia [vfs.ts](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/stores/vfs.ts) 管理當前目錄內容與麵包屑結構。
- [x] 3. 實作 [FileExplorerView.vue](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/views/FileExplorerView.vue) 的雙欄介面：
  - [x] 左側 `320px` 樹狀層級目錄導航（具備縮排層級）。
  - [x] 右側詳細項目列表，帶有檔案名稱、時間與實線黑框邊線 (`border-2 border-black`)。
  - [x] 支援當前路徑 `root > Folder1` 標題顯示。
  - [x] 實作點擊子目錄進入下一層、點擊麵包屑回溯之導航邏輯。
- [x] 4. VFS 導航優化：在非根目錄的右側清單頂部，加入「`..`」去上層的列項目，點擊能返回父目錄。

---

## Phase 5.5: VFS 第 2 階段 - 虛擬目錄異動管理 [已完成 100%]
- [x] 1. 前端 API 與 Pinia 擴充 `/mkdir`、`/rename`、`/move`、`/delete`。
- [x] 2. 實作「新建資料夾」按鈕與輸入彈窗。
- [x] 3. 實作項目 Hover 操作：顯示「重命名」、「移動」與「刪除」圖示，並串接對應 API 與更新重載邏輯。

---

## Phase 5.6: VFS 第 3 階段 - 實體傳輸與分塊上傳 [已完成 70%]
- [x] 1. 實作檔案下載功能，點擊下載按鈕時觸發 `/api/vfs/download/{file_id}`。
- [x] 2. 實作大檔案前端切片，串接分塊上傳三階段工作流 (`/upload/init`, `/upload/chunk`, `/upload/finalize`)。
- [x] 3. 串接 `/upload/status/{upload_id}` 進行斷點續傳進度探測，支援前端恢復上傳。
- [x] 4. 實作前端上傳進度控制面板，展示所有上傳任務，並支援「取消上傳」並調用 `/upload/cancel` API。
- [x] 5. [優化項目] 檔案上傳成功後，延遲 3~5 秒將任務自動從面板清除，或提供手動關閉與清空已完成任務的按鈕。
- [x] 6. [基礎設施] 引入 Redis 快取層與核心模組重構：
  - **Redis 基礎建設**：於 `docker-compose` 加入 `redis:alpine`，並建立 `app/core/cache.py` 管理連線池。由 `main.py` 的 lifespan 負責連線啟動與優雅關閉，採用 Fail-fast 機制。
  - **資料庫搬移**：將 `app/database.py` 移至 `app/core/database.py` 保持模組結構對稱齊平，並全域修正相關的 import 依賴（約 8 處）。
  - **依賴注入**：於 `api/deps.py` 實作 `get_redis` 供路由層使用。
- [x] 7. [優化項目] 解決大檔案（如 3GB）下載無反應、重複點擊導致後端效能超載（起飛）問題。改用「單次臨時 Ticket 憑證」接管原生下載流方案：
  - **後端實作**：
    - 新增 `POST /api/vfs/download/ticket/{file_id}`：校驗 JWT Bearer 權限，生成一次性、有效期 30 秒的隨機 UUID `ticket` 並暫存於 **Redis** (`SET EX 30`)。
    - 修改 `GET /api/vfs/download/{file_id}`：支持自 URL Query 傳入 `?ticket=xxx`。利用 Redis 的 `GETDEL` 原子操作保證憑證的**絕對單次使用**，防堵重放攻擊；有效則以 `FileResponse` 流式傳輸檔案，無效或已過期則直接阻斷回傳 `403 Forbidden`。
  - **前端實作**：
    - 點擊下載時，該檔案列按鈕立刻設為 `disabled` 狀態，圖示改為轉圈 Loading，防使用者焦慮重複狂點。
    - 發送 API 取得單次 Ticket，並透過隱藏的 `<iframe>`（或 `window.open`）載入下載連結，喚醒瀏覽器原生下載管理器（自動展示下載進度與剩餘時間，且記憶體零開銷）。
    - 觸發原生下載 3 秒後，自動解除按鈕禁用狀態，恢復為可下載狀態。
- [x] 8. [優化項目] 將全域錯誤提示（vfsStore.error）自滾動列表區域移出，改為視窗固定懸浮 Toast (fixed z-50)，確保使用者在長列表底部滾動時仍能清楚看到錯誤提示。
- [x] 9. [優化項目] 解決大檔案上傳速度慢的效能瓶頸，降低協定與資料庫等待開銷：
  - **動態分塊大小**：小檔案（<100MB）預設 `2MB`，中檔案（100MB~1GB）使用 `5MB`，大檔案（>=1GB）改用 `10MB` 或 `20MB` 分塊，直接降低 80% 的 HTTP 請求與後端 Session 查詢次數。
  - **併發分塊上傳**：取消單一 for 迴圈序列阻塞式 `await`，實作前端「限制併發數的 Promise 執行池」（例如 Concurrency = 3），同時上傳 3 個分塊，吃滿網路與硬碟寫入頻寬。
- [x] 10. [環境優化項目] (已作廢，未來直接部署於 Linux) 改善 Docker on Windows (WSL2) 掛載磁碟目錄造成的 I/O 延遲（大檔案合併瓶頸）。
- [x] 11. [架構演進/長期優化] 將分塊上傳機制改為「邊傳邊寫 / 隨機寫入 (On-the-fly Random Access Write)」。
  - **(已於 Phase 10 完整實作)**：已改用 Sparse File 預分配與 `seek(offset)` 隨機寫入，徹底消除合併階段的 I/O 延遲。

---

## Phase 7: 系統部分強化與優化 [已完成 100%]
- [x] 1. **2fa replay 防禦**: 目前的 2fa 是 30 秒更新一次，缺乏嚴格的一次性限制，有利暴力破解。（已完成後端與 Redis 的防重放快取驗證鎖）
- [x] 2. **目錄結構快取 (Directory Cache)**: 利用 Redis 實作虛擬目錄架構快取，大幅降低頻繁讀取目錄樹時所造成的 SQLite I/O 開銷。
  - [x] 2.1 改造 `vfs_service.py` 中的 `get_browse_data` 函數（包含自動修復 Root 鍵失效導致的永久 404 問題，與快取狀態整合優化）。
  - [x] 2.2 於 `vfs_service.py` 建立私有 `_clear_browse_cache` 雙刪函數（安全宣告局部變數）。
  - [x] 2.3 改造 `create_folder`、`rename_node`、`move_node`、`delete_node`、`finalize_upload` 呼叫快取清除（包含修復 `delete_node` 在 commit 後讀取已過期屬性的崩潰 Bug）。
  - [x] 2.4 簡化 `api/vfs.py` 裡的 `/ls` 路由以直接調用 `get_browse_data`。
  - [x] 2.5 修正 `create_download_ticket` 雙向映射過期不一致導致的下載鎖死問題。


---

## Phase 5.7: VFS 第 4 階段 - 大檔案上傳韌性強化 (Keep-Alive 衍伸問題)
- [ ] 1. **正式環境連線設定 (Production Parity)**: 開發環境已於 `vite.config.ts` 啟用 Keep-Alive，但正式部署時須在 Nginx 或 Traefik 代理設定中明確啟用對後端 `upstream` 的 `keepalive`，否則正式環境的斷線問題將會重現。
- [x] 2. **前端靜默重試機制 (Retry Mechanism)**: 雖 Keep-Alive 解決了高頻率連線切換 of 底層阻塞，但遇到一般實體網路瞬斷或抖動時，仍會因為單個 chunk 失敗導致整個 3GB 檔案前功盡棄。需在不影響架構的前提下，於前端上傳迴圈中加入單個分塊的自動重試防護。(已於 `vfs.ts` 實作 3 次延遲重試)

---

## Phase 8: 參數與環境變數抽取 (設定分離版) [已完成 100%]
- [x] 1. 於專案根目錄建立新環境設定檔 `.env` 存放前端代理設定。
- [x] 2. 修改 [vite.config.ts](file:///d:/Project/file-explorer/vite.config.ts) 引入 `loadEnv` 讀取前端代理變數。
- [x] 3. 於後端 [server/.env](file:///d:/Project/file-explorer/server/.env) 新增伺服器與 Redis 快取最大連線設定、下載憑證 TTL、限流次數、合併緩衝、2FA 權杖有效期限等變數。
- [x] 4. 修改後端 [config.py](file:///d:/Project/file-explorer/server/app/core/config.py) 讀取並定義以上新增的各項設定值。
- [x] 5. 修改後端 [main.py](file:///d:/Project/file-explorer/server/app/main.py) 的 `uvicorn.run` 使其套用環境變數的 Host 與 Port。
- [x] 6. 修改後端 [cache.py](file:///d:/Project/file-explorer/server/app/core/cache.py) 以環境變數設定 Redis 連線池最大連線數。
- [x] 7. 修改 [vfs_service.py](file:///d:/Project/file-explorer/server/app/services/vfs_service.py) 套用下載憑證 TTL 與限流設定。
- [x] 8. 修改 [storage.py](file:///d:/Project/file-explorer/server/app/filesystem/storage.py) 套用檔案合併讀取緩衝區大小設定。
- [x] 9. 修改 [jwt.py](file:///d:/Project/file-explorer/server/app/security/jwt.py) 套用 2FA 臨時驗證權杖有效期限。
- [x] 10. 本地前後端測試與執行驗證。

---

## Phase 9: 系統長期架構重構與優化建議 [待規劃]

根據架構評估，以下為各模組改用 OOP 與依賴注入 (DI) 的必要性與優先級排序：

- [x] 1. **🔴 [極高優先] Phase 9 (Part 1) 重構儲存層與暫存區為 OOP 介面/多型設計 (Strategy Pattern)**：
  * **目標**：實作 `BaseStorage(ABC)` 與 `LocalDiskStorage`，取代 `storage.py` 與 `chunks.py`。
  * **策略**：在 `__init__.py` 設定暫時的 `storage_instance` 以相容舊程式碼。

- [x] 2. **🟡 [中高優先] Phase 9 (Part 2) 重構 Redis 連線管理為 OOP 單例**：
  * **背景原因**：`app/core/cache.py` 定義了 `global redis_client`，若其他模組在 `init_redis()` 執行前就 import 會拿到 `None`，容易引發「初始化時間差」的潛在崩潰。
  * **優化方案**：重構為 `RedisManager` 單例類別，確保呼叫時保證連線池已被正確初始化，消滅全域變數問題。

- [x] 3. **🔴 [極高優先] Phase 9 (Part 3) 重構服務層 (Service Layer) 為實例化物件與依賴注入 (DI)**：
  * **目標**：將靜態方法改為實例方法，並搭配 FastAPI 的 `Depends` 機制自動注入相依資源。
  * **⚠️ 重要提醒**：實作完成後，務必**拔除** Part 1 留在 `__init__.py` 的全域暫時變數與代理函數！

- [x] 4. **🟢 [偏低優先 / 視需求] 評估安全與認證輔助模組是否需 OOP 化**：
  * **背景原因**：`hasher.py`, `jwt.py`, `otp.py` 目前為純函數式設計，內部直接依賴 `settings.SECRET_KEY`。
  * **評估結果**：由於加密演算法本身是**無狀態 (Stateless)** 且極度單純，硬包裝成類別 (如 `JWTManager`) 雖然工整，但增加使用時的繁瑣度。建議此部分**維持現狀**即可，除非未來專案發展出多租戶或需在測試中頻繁動態抽換金鑰的需求。

- [x] 5. **🟡 [中高優先] Phase 9 (Part 5) 引入 `TYPE_CHECKING` 優化全域模組引用**：
  * **目標**：全面掃描所有 `.py` 檔案，將僅用於 Type Hint 的頂層 `import` 移入 `if TYPE_CHECKING:` 區塊內，並搭配 `from __future__ import annotations`。
  * **背景原因**：徹底消滅專案變大後容易引發的「循環依賴 (Circular Import)」風險，同時減少 FastAPI 啟動時的 Runtime Overhead。

---

## Phase 10: 大檔案上傳架構重構 (隨機寫入 + Redis 進度追蹤) [待執行]

為了徹底解決大檔案在 `finalize_upload` 階段發生的合併 I/O 延遲，將上傳機制重構為「實體 Sparse File 預分配與 Random Access Write」，並由 Redis 接管高頻進度追蹤。

- [x] **Step 1: 基礎層 (Base Layer) - 資料庫模型與 API Schema**
  - 修改 `UploadSession` 模型，加入 `total_size` (檔案總大小) 與 `chunk_size` (切塊大小)。
  - 修改 `schemas.vfs.UploadInitRequest` 補上對應的請求驗證欄位。
- [x] **Step 2: 基礎層 (Base Layer) - 實體儲存策略 (`filesystem/local.py`)**
  - 實作 `init_sparse_file` 瞬間分配硬碟空間 (`truncate`)。
  - 改寫 `save_chunk`，開啟 `.tmp` 檔並使用 `seek(offset)` 隨機寫入。
  - 實作 `finalize_file` 以串流方式驗證 SHA256 並正式 rename，同時刪除舊有的 `merge_from_chunks`。
- [x] **Step 3: 執行層 (Logic Layer) - 核心業務流程 (`services/vfs_service.py`)**
  - 串接 `init_upload` (預分配) 與 `upload_chunk` (計算 offset 並寫入)。
  - 整合 Redis `SADD` 追蹤已上傳分塊，將 `get_upload_status` 改為查詢 Redis。
  - 調整 `finalize_upload` 與 `cancel_upload` 以配合新的單一 `.tmp` 檔案機制與清除 Redis 鎖。
- [x] **Step 4: 管理層 (Management Layer) - GC 背景清理 (`gc/core.py`)**
  - 調整 Phase 2 孤兒暫存清理邏輯，由尋找「孤兒目錄」改為尋找結尾為 `.tmp` 的「孤兒檔案」。

---

## Phase 11: 重新設計大檔案上傳的生命週期與 GC 清理邏輯 [已解決 100%]

在 Phase 10 的重構中，我們將上傳進度完全轉交給 Redis 以解決 SQL 效能問題，但這引發了嚴重的業務邏輯 Bug 與架構不合理之處：

- **致命 Bug (活躍狀態判斷斷層)**：SQL 的 `UploadSession.created_at` 從建立後不再更新。若大檔案傳輸過程超過系統設定的 GC 門檻 (如 24 小時)，即使客戶端仍在積極上傳 (Redis TTL 依然活躍)，GC Phase 1 仍會因 SQL 紀錄超時而將活躍會話強行誤殺。

**[實作解法]**：
- [x] GC Phase 1 ( `gc/core.py` 的 `gc_expired_sessions` ) 已實作 Redis 活躍防護校驗。在刪除超時 SQL 會話前，會主動透過 `redis_client.exists` 確認 Redis 是否活躍。
- [x] 若活躍，自動將 `UploadSession.created_at` 展延至當前時間，保護活躍會話不被誤殺，完美解決斷層問題。

---

## Phase 12: 跨資料夾斷點續傳支援 (Cross-Folder Resume) [已完成 100%]

目前斷點續傳能跨資料夾觸發，但檔案最終歸宿會被鎖死在最初上傳的資料夾。為了保留不重複傳輸的效能優勢，並符合使用者「在哪個資料夾發起，檔案就落在哪個資料夾」的直覺體驗，預計實作以下改動：

- [x] 1. **後端 Schema 修改**：新增 `UploadResumeRequest`，讓續傳請求支援傳入 `target_folder_id` (Optional)。
- [x] 2. **後端服務層修改**：於 `vfs_service.py` 實作全新的 `resume_upload` 函數。
  - 在改變目標資料夾前，**先做檔名衝突檢查** (包含實體檔案與活躍上傳)。
  - 若無衝突，動態更新 `UploadSession.target_folder_id`。
- [x] 3. **後端 API 路由修改**：將原本用來檢查續傳狀態的 `GET /upload/status/{upload_id}` 邏輯轉移或擴充到新的 `POST /upload/resume` 介面，以符合 RESTful 語義。
- [x] 4. **前端 API 與 Store 修改**：
  - 更新 `src/api/vfs.ts` 提供 `resumeUpload` 呼叫。
  - 修改 `src/stores/vfs.ts` 的 `executeUploadTask`，在發現快取時呼叫 `resumeUpload` 而非 `getUploadStatus`。若因衝突而回傳錯誤，則自動清除 LocalStorage 快取並退回正常的重新上傳流程。
- [x] 5. **活躍上傳會話管理與操作介面 (單一面板 7 態共存 UX 優化)**：
  - **後端 API 擴充**：
    - 實作 `GET /api/vfs/upload/sessions`，使用 `SCARD` 與 Redis Pipeline 高效計算每個會話的 `uploaded_chunks_count` 並回傳活躍任務清單。
  - **前端 Pinia 狀態機改造 (`vfs.ts`)**：
    - **不分區設計**：所有任務統一在同一個 `uploadTasks` 陣列與 UI 面板中呈現，並藉由擴充至 7 種嚴格的狀態機來驅動 UI 變化：
      1. `checking`: 初始化檢查中。
      2. `uploading`: 積極上傳傳輸中。
      3. `finalizing`: 傳輸完畢，後端合併校驗中。
      4. `success`: 上傳完成 (顯示綠色，3秒後自動移除)。
      5. `failed`: 發生致命錯誤 (顯示紅色，需手動點擊 X 移除)。
      6. `paused`: 手動暫停 (記憶體仍有實體檔案，點擊繼續可無縫恢復)。
      7. `waiting_for_file`: F5 重新整理後從 API 拉回的歷史任務 (記憶體無檔案，點擊繼續需強制彈出檔案選擇窗，嚴格校驗後恢復)。
    - **核心 Action 重構與資料融合防護**：
      - `fetchActiveTasksAction`: 網頁載入時拉取後端 API，比對本地 `uploadTasks` 進行雙向校正：
        - **正向補齊**：本地不存在的會話，以 `'waiting_for_file'` 加入，避免覆蓋正在上傳的任務。
        - **反向清理 (幽靈任務防護)**：本地為 `'waiting_for_file'` 或 `'paused'` 的任務若未出現在 API 回傳中，代表已遭後端 GC 清除或被其他裝置取消，應將其從本地陣列中移除或標記為 `failed`。
      - `pauseUploadAction`: 中斷 Axios 傳輸並轉為 `'paused'`，**嚴禁呼叫後端 cancel API** 以保留實體碎片與 DB 紀錄。

---

## Phase 13: 前端視覺特效與 UI 優化 [已完成 100%]
- [x] 1. **實作滑鼠閃電軌跡特效**: 新增 `LightningCursor.vue` 元件，透過 Canvas 繪製跟隨滑鼠的隨機閃電軌跡，並支援 180 度反向噴發效果。
- [x] 2. **特效參數重構**: 將閃電的生存時間、分岔機率、抖動幅度與長度等魔術數字抽出至 `CONFIG` 設定區塊，提升可維護性。
- [x] 3. **設定頁面版型對齊**: 重新設計 `SettingsView.vue` 佈局，分離標題與內容區塊，使其與 `FileExplorerView.vue` 的終端機毛玻璃風格維持一致。
- [x] 4. **進度條 UI 優化**: 增加上傳進度條的高度 (`h-4`) 與間距，解決進度百分比文字與框線貼太齊的壓迫感。

---

## Phase 14: 上線部署與網路連線架構規劃 (私有雲終極型態) [待執行]

針對未來上線部署，採用 **「私有 DNS + DNS-01 憑證驗證」** 的雙軌架構，實現無限制高速、專屬網域與絕對安全：

- [ ] **1. Cloudflare (負責 DNS 與憑證驗證)**
  - **角色定位**：僅作為網址導航與 Let's Encrypt 綠色鎖頭的發放公證人。
  - **實作細節**：將專屬網域 (如 `files.yourdomain.com`) 以 `A 紀錄` 指向伺服器的 Tailscale 內部 IP (100.x.x.x)。
  - **⚠️ 關鍵注意**：務必關閉 CF 代理 (灰色雲朵)，避免流量被 CF 攔截與限速。CF Tunnel 在此高速架構下不適用。

- [ ] **2. Tailscale (負責實體資料傳輸)**
  - **角色定位**：點對點 (P2P) 高速加密連線隧道。
  - **實作細節**：完全繞過公網限速，直接吃滿客戶端與伺服器端的真實頻寬，非常適合大檔案 (數十 GB) 上下傳。
  - **安全性**：伺服器無需在路由器設定 Port Forwarding，實現 Zero Trust (零信任) 防護，阻絕公網掃描與 DDoS 攻擊。

- [ ] **3. Nginx Proxy Manager (負責反向代理與流量管理)**
  - **角色定位**：大門守衛，負責掛載 HTTPS 憑證、反向代理轉發與頻寬控管。
  - **自動憑證**：透過 NPM 內建的 Cloudflare API (DNS-01 挑戰)，自動為私有 IP (100.x.x.x) 申請並展延合法的 TLS/SSL 憑證。
  - **流量管理**：
    - **速度限制 (Bandwidth Throttling)**：若需限制單一用戶下載速度，可於 NPM 進階設定配置 `limit_rate`。
    - **Keep-Alive 支援**：明確啟用 `upstream keepalive` (對應 Phase 5.7)，防止大檔案分塊上傳時頻繁建立連線導致被踢。

- [ ] **4. FastAPI 後端 (負責應用層限流與業務)**
  - **角色定位**：處理 API 請求次數限制與核心業務邏輯。
  - **實作細節**：利用 Redis 的 Rate Limiting 機制，防範前端異常的重複高頻請求 (例如狂點下載)。
