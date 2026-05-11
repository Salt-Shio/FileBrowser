# 分階段實作計畫：VFS API 與系統初始化

為了降低開發風險，將 Step 2.3 & 2.4 的內容拆分為四個獨立階段。

## 階段 1：基礎架構與數據結構 (Schemas)
**目標**：確保 Package 匯出正確，並定義 API 回應格式。

- **[MODIFY] [schemas/__init__.py](file:///d:/Project/file-explorer/server/app/schemas/__init__.py)**: 補上 `from . import vfs`。
- **[MODIFY] [schemas/vfs.py](file:///d:/Project/file-explorer/server/app/schemas/vfs.py)**: 新增 `BrowseResponse` 模型。

## 階段 2：安全門檻整合 (Security Dependency)
**目標**：實作能將 JWT Token 轉換為資料庫 User 物件的依賴項。

- **[NEW] [api/deps.py](file:///d:/Project/file-explorer/server/app/api/deps.py)**: 
    - 實作 `get_current_user(token, db)` 函式。
    - 使用 `OAuth2PasswordBearer` 提供 Swagger UI 的 Token 輸入框支援。

## 階段 3：業務邏輯擴充 (Service Layer)
**目標**：強化 Service 層，使其具備自動初始化根目錄與整合查詢能力。

- **[MODIFY] [services/vfs_service.py](file:///d:/Project/file-explorer/server/app/services/vfs_service.py)**:
    - 實作 `get_or_create_root()`：懶載入初始化邏輯。
    - 實作 `get_browse_data()`：三路查詢整合。
    - 實作 `search_nodes()`：模糊關鍵字搜尋。

## 階段 4：路由註冊與 API 實作 (API Router)
**目標**：將功能開放給前端，並完成總路由註冊。

- **[NEW] [api/vfs.py](file:///d:/Project/file-explorer/server/app/api/vfs.py)**: 實作 `/ls` 與 `/search`。
- **[MODIFY] [api/__init__.py](file:///d:/Project/file-explorer/server/app/api/__init__.py)**: 註冊 `vfs_router`。

---

## 架構優化紀錄 (Architecture Notes)

### 1. 依賴項解耦 (Dependency Decoupling)
- **原則**：採用 `app/api/deps.py` 作為所有注入依賴項 (Depends) 的集中轉運站。
- **優點**：
    - 確保 `app/security/jwt.py` 保持「純邏輯」狀態，不依賴資料庫。
    - 防止跨層級調用產生的循環引用 (Circular Import) 問題。
    - 統一 API 路由的匯入來源，降低維護成本。

### 2. 未來擴充候選 (Potential Dependencies)
- `get_pagination`：通用分頁參數過濾。
- `get_current_root`：自動確保使用者擁有根目錄並回傳根目錄物件。
- `check_permission`：基於角色或資源擁有權的權限檢查。

## 驗證流程 (每階段結束後執行)
1. 階段 1：確認匯入 `schemas.vfs` 無報錯。
2. 階段 2：確認 `get_current_user` 能正確解析現有 Token。
3. 階段 3：執行單元測試，模擬新使用者登入是否會自動產生 Root。
4. 階段 4：通過 Swagger UI 進行端到端 (E2E) 測試。
