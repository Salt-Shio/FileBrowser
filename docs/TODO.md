# 專案實作與 Figma 對齊 TODO 清單

## Phase 5.1: Settings & 2FA 安全管理 [已完成 100%]
- [x] 1. 安裝 `qrcode.vue` 處理 QRCode 生成
- [x] 2. 更新 `src/api/auth.ts`，封裝 `/2fa/generate`, `/2fa/enable`, `/2fa/disable` 等 API。
- [x] 3. 更新 `src/stores/auth.ts`，擴充 2FA 相關操作狀態管理。
- [x] 4. 實作 `src/components/auth/TwoFactorEnableModal.vue` 元件 (依照 Figma UI 設計)。
- [x] 5. 實作 `src/views/SettingsView.vue` 畫面與互動邏輯 (包含表單與呼叫 Modal)。
- [x] 6. 測試完整的 2FA 啟用流程與後續登入驗證，並等待使用者確認完成。

---

## Phase 5.2: 全域導航與頁面麵包屑優化 [待執行]
- [ ] 1. 調整 [App.vue](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/App.vue) 中的 Navbar 選單字體比例（對齊 Figma 的大字體風格，標題 `55px`，選單 `45px`）。
- [ ] 2. 在全頁頂部加入「`主頁 --> [目前頁面]`」的白色底線麵包屑路徑顯示區。
- [ ] 3. 全域字體優化：完整引入並套用 Figma 中指定的 'Inter' 字體系列（對齊字重 font-weight 與抗鋸齒渲染）。

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

## Phase 5.6: VFS 第 3 階段 - 實體傳輸與分塊上傳 [已完成 50%]
- [x] 1. 實作檔案下載功能，點擊下載按鈕時觸發 `/api/vfs/download/{file_id}`。
- [x] 2. 實作大檔案前端切片，串接分塊上傳三階段工作流 (`/upload/init`, `/upload/chunk`, `/upload/finalize`)。
- [x] 3. 串接 `/upload/status/{upload_id}` 進行斷點續傳進度探測，支援前端恢復上傳。
- [x] 4. 實作前端上傳進度控制面板，展示所有上傳任務，並支援「取消上傳」並調用 `/upload/cancel` API。
- [x] 5. [優化項目] 檔案上傳成功後，延遲 3~5 秒將任務自動從面板清除，或提供手動關閉與清空已完成任務的按鈕。
- [ ] 6. [基礎設施] 引入 Redis 快取層與核心模組重構：
  - **Redis 基礎建設**：於 `docker-compose` 加入 `redis:alpine`，並建立 `app/core/cache.py` 管理連線池。由 `main.py` 的 lifespan 負責連線啟動與優雅關閉，採用 Fail-fast 機制。
  - **資料庫搬移**：將 `app/database.py` 移至 `app/core/database.py` 保持模組結構對稱齊平，並全域修正相關的 import 依賴（約 8 處）。
  - **依賴注入**：於 `api/deps.py` 實作 `get_redis` 供路由層使用。
- [ ] 7. [優化項目] 解決大檔案（如 3GB）下載無反應、重複點擊導致後端效能超載（起飛）問題。改用「單次臨時 Ticket 憑證」接管原生下載流方案：
  - **後端實作**：
    - 新增 `POST /api/vfs/download/ticket/{file_id}`：校驗 JWT Bearer 權限，生成一次性、有效期 30 秒的隨機 UUID `ticket` 並暫存於 **Redis** (`SET EX 30`)。
    - 修改 `GET /api/vfs/download/{file_id}`：支持自 URL Query 傳入 `?ticket=xxx`。利用 Redis 的 `GETDEL` 原子操作保證憑證的**絕對單次使用**，防堵重放攻擊；有效則以 `FileResponse` 流式傳輸檔案，無效或已過期則直接阻斷回傳 `403 Forbidden`。
  - **前端實作**：
    - 點擊下載時，該檔案列按鈕立刻設為 `disabled` 狀態，圖示改為轉圈 Loading，防使用者焦慮重複狂點。
    - 發送 API 取得單次 Ticket，並透過隱藏的 `<iframe>`（或 `window.open`）載入下載連結，喚醒瀏覽器原生下載管理器（自動展示下載進度與剩餘時間，且記憶體零開銷）。
    - 觸發原生下載 3 秒後，自動解除按鈕禁用狀態，恢復為可下載狀態。
- [ ] 8. [優化項目] 解決大檔案上傳速度慢的效能瓶頸，降低協定與資料庫等待開銷：
  - **動態分塊大小**：小檔案（<100MB）預設 `2MB`，中檔案（100MB~1GB）使用 `5MB`，大檔案（>=1GB）改用 `10MB` 或 `20MB` 分塊，直接降低 80% 的 HTTP 請求與後端 Session 查詢次數。
  - **併發分塊上傳**：取消單一 for 迴圈序列阻塞式 `await`，實作前端「限制併發數的 Promise 執行池」（例如 Concurrency = 3），同時上傳 3 個分塊，吃滿網路與硬碟寫入頻寬。
- [ ] 9. [環境優化項目] 改善 Docker on Windows (WSL2) 掛載磁碟目錄造成的 I/O 延遲（大檔案合併瓶頸）。評估之三種改善方案與優缺點：
  - **方案 A：改用 Docker 具名卷 (Named Volume) 存放上傳數據 (如 `file-explorer-data:/app/data`)**
    - *優點*：I/O 速度大升 5~10 倍（原生 EXT4 讀寫），3GB 大檔案合併從近一分鐘降至數秒。
    - *缺點*：Windows 本機目錄中無法直觀看到 `./data` 下的實體檔案，需在 WSL2 終端機或 WSL 虛擬磁碟路徑中走訪。
  - **方案 B：將整個專案專案目錄移入 WSL2 原生 Linux 家目錄開發**
    - *優點*：不跨 OS 邊界，維持原本的 Volume 掛載，同時享有本機硬碟的原生讀寫效能。
    - *缺點*：開發習慣需要適應，須使用 VS Code `Remote - WSL` 插件遠端連入虛擬機開發。
  - **方案 C：從程式面改用「隨機寫入 (On-the-fly Random Access Write)」（同 TODO 6）**
    - *優點*：物理寫入量減半，最後 Finalize 幾乎秒開，且 Windows 目錄中仍可看見實體檔案。
    - *缺點*：後端上傳 Session 狀態探測（斷點續傳）必須重構，工程改動規模較大。
- [ ] 10. [架構演進/長期優化] 將分塊上傳機制改為「邊傳邊寫 / 隨機寫入 (On-the-fly Random Access Write)」，以消除結算合併（Finalize）階段的大檔案物理合併 I/O 延遲，優化伺服器 SSD 寫入壽命。

---

## Phase 7: 系統部分強化與優化
- [ ] 1. **2fa replay 防禦**: 目前的 2fa 是 30 秒更新一次，缺乏嚴格的一次性限制，有利暴力破解。
- [ ] 2. **目錄結構快取 (Directory Cache)**: 利用 Redis 實作虛擬目錄架構快取，大幅降低頻繁讀取目錄樹時所造成的 SQLite I/O 開銷。