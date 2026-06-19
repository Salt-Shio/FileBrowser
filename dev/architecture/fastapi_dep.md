# FastAPI 依賴注入 (Dependency Injection) 指南

這份文件說明了專案中如何使用 `Depends` 以及為何採用 `deps.py` 的架構設計。

**原先是看到在 jwt.py import database 太智障了，直覺上就有點問題**

## 1. 核心概念：什麼是 `Depends`？

`Depends` 是 FastAPI 的靈魂。它的思維是：**「在執行主邏輯（API 函式）之前，先由系統自動準備好資源或進行檢查。」**

### 廚房比喻
*   **API 函式**：主廚 (Chef)。負責炒菜（業務邏輯）。
*   **Depends**：二廚/助手 (Assistant)。負責洗鍋子 (`get_db`)、檢查主廚識別證 (`get_current_user`)。
*   **優點**：主廚不需要管鍋子哪裡來，只要專心炒菜。如果鍋子沒洗好或識別證不對，主廚根本不需要進廚房。

---

## 2. 為什麼要使用 `deps.py` 模式？

在專案中建立 `app/api/deps.py` 是一個廣泛認可的「潛規則」（由 FastAPI 作者 Tiangolo 推廣）。

### A. 解決循環引用 (Circular Imports)
這是最務實的原因。`deps.py` 作為一個中間層，可以匯入 `database`、`models`、`security`。而這些底層模組不需要匯入 `deps.py`。
這保證了依賴流向是單向的：`Routers -> Deps -> Infrastructure`。

### B. 關注點分離 (Separation of Concerns)
*   **`security/jwt.py`**：純工具，只管加密算法，不認識資料庫。
*   **`api/deps.py`**：組裝廠，負責把加密工具跟資料庫連線組裝成 API 可用的依賴項。

### C. 統一入口
所有的路由 (`auth.py`, `vfs.py`) 只要統一匯入 `from app.api import deps` 就能拿到所有資源，不需要去記憶複雜的目錄結構。

---

## 3. 常見的依賴項類型

| 類型 | 範例 | 職責 |
| :--- | :--- | :--- |
| **資源提供** | `get_db` | 負責提供資料庫會話 (Session)，並在結束後自動關閉。 |
| **服務實例化 (DI)** | `get_vfs_service` | 將 `db`, `redis_client`, `storage` 等基礎資源組裝後，注入並回傳 Service 物件。 |
| **安全守衛** | `get_current_user` | 驗證 Token 合法性，並直接從資料庫抓出 User 物件。 |
| **邏輯檢查** | `get_current_active_user` | 依賴於 `get_current_user`，進一步檢查帳號是否被停權。 |
| **參數過濾** | `get_pagination` | 統一處理分頁參數 (skip, limit)。 |

---

## 4. 開發建議

1.  **優先使用 `deps.py`**：除非該依賴項極度特殊且只給單一路由使用，否則應優先放入 `deps.py`。
2.  **保持純粹**：`deps.py` 的職責是「準備與檢查」，不要在裡面寫太重的業務邏輯，業務邏輯應保留在 `services/`。
3.  **善用鏈式依賴**：利用依賴項可以互相依賴的特性，將複雜的檢查拆解成多個小型的 `Depends`。
