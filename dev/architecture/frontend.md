# 前端極致整潔實作計畫書 (Frontend High-Standard Implementation Plan)

## 1. 架構核心原則 (Architectural Principles)
*   **高度組件化 (High Componentization)**: 遵循原子設計 (Atomic Design)，UI 與業務邏輯嚴格分離。
*   **關注點分離 (SoC)**: API 請求、狀態管理、介面展示各司其職。
*   **型別驅動 (Type-Driven)**: 全程使用 TypeScript 定義資料流，拒絕 `any`。
*   **視覺規範 (Design System)**: 嚴格「簡單 + 無色 (Simple & Colorless)」，僅限黑白灰。

---

## 2. 詳細實作步驟 (Detailed Steps)

### 第一階段：基礎設施與原子 UI 庫 (Foundation & Atomic UI)
1.  **環境架構佈署**:
    *   安裝核心依賴：`pinia`, `vue-router`, `axios`, `lucide-vue-next`。
    *   配置 TS：`tsconfig.json` 設定嚴格模式與 `@/*` 路徑別名。
    *   Tailwind 4 深度配置：在 CSS 中定義 `--color-mono-x` 變數系列。
2.  **建立原子組件 (`src/components/ui/`)**:
    *   `BaseButton.vue`: 支援 Ghost (邊框) 與 Solid (反色) 模式。
    *   `BaseInput.vue`: 具備 Focus 狀態的線條感設計。
    *   `BaseCheckbox.vue`: 用於法律驗證，極簡方框。
    *   `BaseModal.vue`: 基礎彈窗框架，用於 2FA 或設定。
3.  **全域攔截器**:
    *   Axios 實例化，實作 Response 攔截器處理 401 登出與 2FA 流程引導。

### 第二階段：註冊與法律驗證流 (Register & Legal)
1.  **法律聲明組件**: 建立 `LegalVerification.vue`，確保註冊前必須勾選服務條款。
2.  **註冊邏輯封裝**:
    *   `api/auth.ts`: 實作 `register` 調用。
    *   `RegisterView.vue`: 呼叫 `BaseInput` 與 `LegalVerification` 組合頁面。

### 第三階段：登入與 2FA 狀態機 (Login & 2FA State Machine)
1.  **2FA 邏輯狀態化**:
    *   `authStore`: 管理 `login_stage` (PASSWORD -> TOTP -> COMPLETED)。
    *   暫存 `two_fa_token` 用於二階段驗證。
2.  **多步驟介面**:
    *   `LoginForm.vue`: 第一階段帳密。
    *   `OTPForm.vue`: 第二階段 6 位數代碼。
3.  **條件式路由**: 實作 `Navigation Guard`，確保未完成 2FA 的用戶無法進入主頁。

### 第四階段：檔案瀏覽器核心 (File Explorer - Componentized)
1.  **資料型別定義**: 建立 `src/types/vfs.ts`，與後端 Pydantic Models 1:1 對應。
2.  **VFS 服務封裝**: `stores/vfs.ts` 處理 `/api/vfs/ls` 資料並維持響應式。
3.  **高度拆解的組件結構**:
    *   `BreadcrumbBar.vue`: 解析並渲染層級路徑。
    *   `FileToolbar.vue`: 包含上傳、新增資料夾、搜尋。
    *   `FileGrid.vue` / `FileList.vue`: 兩種檢視模式。
    *   `FileNode.vue`: 單個檔案/資料夾的視覺與右鍵選單邏輯。

### 第五階段：設定頁與 2FA 管理 (Settings & Security)
1.  **設定面板**: `views/SettingsView.vue`。
2.  **2FA 管理邏輯**:
    *   **Enable**: 請求 Secret -> 顯示 QR Code -> 輸入首次 OTP 驗證 -> 正式啟用。
    *   **Disable**: 輸入當前 OTP -> 停用。
    *   組件化：`2FAEnableModal.vue`, `2FADisableModal.vue`。

### 第六階段：進階檔案操作 (Advanced Ops)
1.  **分塊上傳引擎**:
    *   `utils/uploader.ts`: 獨立的 class 處理檔案切片、Hash 計算、併發控制。
    *   `UploadProgress.vue`: 位於頁面底部的極簡進度提示列。
2.  **批次操作**: 實作多選、搬移、刪除。

---

## 3. 代碼整潔度標準 (Clean Code Standards)
*   **Script Setup**: 統一使用 `<script setup lang="ts">`。
*   **Props & Emits**: 必須明確定義 Type，嚴禁隱式傳參。
*   **No Magic Values**: 顏色、間距、API 路徑必須透過常量或 CSS 變數管理。
*   **Logic Extraction**: 超過 30 行的業務邏輯必須抽取至 `composables/` (例如 `useAuth.ts`, `useFileList.ts`)。

## 4. 視覺規範 (Visual Specs)
*   **Color**: `#000`, `#FFF`, `#121212` (Bg), `#262626` (Border), `#A3A3A3` (Muted Text)。
*   **Radius**: `0px` 或 `4px` (按鈕), `25px` (大型 Card)。
*   **Border**: `1px` 為主，Focus 時 `2px`。
