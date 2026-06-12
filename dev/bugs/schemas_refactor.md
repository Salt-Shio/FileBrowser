# Schema 架構重構與規範紀錄 (Schemas Refactor)

本文件紀錄了專案在 Phase 2 結束後的 Schema 架構診斷結果，並定義了 Phase 3 開始後的重構方向與開發規範。

## 1. 目前問題診斷 (Current Issues)

### A. 模型缺失
*   **缺少 `user` 相關模型**：目前沒有定義 `UserResponse` 與 `Token` 模型，導致認證 API 只能回傳原始字典 (Dict)。
*   **安全隱患**：`api/auth.py` 的端點缺少 `response_model` 宣告，無法確保敏感欄位（如密碼哈希）絕對不會外洩。

### B. 職責耦合
*   **Service 層依賴 API 模型**：`AuthService` 的函式參數直接接收了 API 專用的 `LoginRequest` 模型。這導致業務邏輯層與資料傳輸層產生了不必要的耦合。

### C. 風格不統一
*   **回傳值不一致**：`AuthService` 回傳 `Dict`，而 `VFSService` 回傳 `Model`。
*   **導入風格衝突**：API 層使用模組導入 (`from app import schemas`)，Service 層使用類別導入 (`from app.schemas.vfs import Breadcrumb`)。

---

## 2. 重構方針 (Refactoring Plan)

### A. 實施「原始參數優先」原則 (Primitive Parameters First)
*   **規範**：Service 層的函式應僅接收原始資料型別（如 `str`, `int`, `UUID`），而非直接接收 Schema 物件。
*   **重構理由 (Rationale)**：
    1.  **解除層次耦合**：避免 Service 層需要知道 API 層的數據傳輸格式。Service 只處理業務，不處理「拆包裹」。
    2.  **提高複用性**：讓 Service 可以輕易地被 CLI 腳本、定時任務或其他內部模組調用，而不需要為了傳參去實例化一個 Pydantic 模型。
    3.  **簡化單元測試**：測試 Service 時只需傳入字串或數字，不需要構造複雜的 Schema 物件。
    4.  **防範規格變更**：當 API 規格（JSON 結構）變動時，只要傳遞的內容不變，Service 層代碼無需更動。

### B. 強制 API 層回傳模型 (Strict Response Models)
*   **規範**：所有對外開放的 API 端點，**必須** 顯式宣告 `response_model`。
*   **目的**：利用 Pydantic 的自動過濾機制，確保回傳資料的安全性與一致性。

### C. 補齊與標準化模型
*   **新增 `app/schemas/user.py`**：定義 `UserResponse` 與 `Token` 結構。
*   **統一導入風格**：
    *   **API 層**：統一使用 `from app import schemas`。
    *   **Service 層**：統一使用 `from app.schemas.xxx import XXX`。

---

## 3. 執行清單 (Detailed Execution Plan)

### Step 3.0.1: 建立基礎規格 (Missing Schemas)
- [x] 建立 `app/schemas/user.py` (待測試)。
- [x] 定義 `UserResponse` (過濾敏感欄位) (待測試)。
- [x] 定義 `Token` 與 `TokenPayload` (規範 JWT 回傳格式) (待測試)。

### Step 3.0.2: Service 層去耦合 (Service Decoupling)
- [x] 重構 `AuthService.login`：參數改為 `username, password` (待測試)。
- [x] 重構 `AuthService.verify_2fa`：參數改為 `username, otp_code` (待測試)。
- [x] 確保 Service 回傳值符合預期的資料結構 (待測試)。

### Step 3.0.3: API 層強化守門 (API Security)
- [x] 更新 `api/auth.py`：為所有端點補齊 `response_model` (待測試)。
- [x] 更新 `api/auth.py`：將傳入 Service 的參數由 Schema 物件拆解為原始變數 (待測試)。

### Step 3.0.4: 新增驗證端點 (/me)
- [x] 在 `api/auth.py` 新增 `/me` 路由 (待測試)。
- [x] 使用 `response_model=schemas.user.UserResponse` (待測試)。
- [x] 透過 `deps.get_current_user` 注入使用者物件，驗證 Schema 是否成功過濾敏感欄位 (待測試)。

### Step 3.0.5: 風格標準化 (Standardization)
- [x] 統一所有 Service 的導入風格 (具體類別導入) (待測試)。
- [x] 統一所有 API 的導入風格 (模組級導入) (待測試)。
- [x] 檢查 `vfs_service.py` 複雜回傳值是否需要結構化 (待測試)。
