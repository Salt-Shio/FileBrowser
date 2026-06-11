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

## Phase 5.3: 設定頁面修改密碼功能整合 [待執行]
- [ ] 1. 後端新增密碼更變與確認之 API 路由與對應 Service。
- [ ] 2. 前端 [SettingsView.vue](file:///c:/Users/salt/Desktop/Project/FileBrowser/src/views/SettingsView.vue) 對接後端修改密碼 API，並將「確認」更變的邏輯落實。

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

## Phase 5.6: VFS 第 3 階段 - 實體傳輸與分塊上傳 [當前核心任務 🎯]
- [ ] 1. 實作檔案下載功能，點擊下載按鈕時觸發 `/api/vfs/download/{file_id}`。
- [ ] 2. 實作大檔案前端切片，串接分塊上傳三階段工作流 (`/upload/init`, `/upload/chunk`, `/upload/finalize`)。
- [ ] 3. 串接 `/upload/status/{upload_id}` 進行斷點續傳進度探測，支援前端恢復上傳。
- [ ] 4. 實作前端上傳進度控制面板，展示所有上傳任務，並支援「取消上傳」並調用 `/upload/cancel` API。
