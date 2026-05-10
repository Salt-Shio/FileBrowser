# 專案架構重構計畫 (Refactor Plan) - 修正版

根據對 SQLAlchemy 2.0 與 `aiosqlite` 的深入查證，我們將採取「最穩定且高效」的架構方案。

## 1. 核心問題診斷 (Current Issues)
*   **職責重疊 (Redundancy)**：`main.py` 與 `database.py` 同時在設定 WAL 模式，造成邏輯混亂。
*   **語法錯誤**：`main.py` 中的 `conn.execute` 誤用了字串而非 `text()` 物件。
*   **Schema 耦合**：`api/auth.py` 內部定義了 Pydantic 模型，應抽離至 `schemas/`。
*   **匯入不便**：缺乏 `models/__init__.py` 導致主程式匯入路徑過於零碎。

## 2. 最終確定的架構設計

### A. 資料庫優化：事件監聽器 (Event Listener)
*   **位置**：`app/database.py`
*   **做法**：保留並強化 `@event.listens_for(engine.sync_engine, "connect")`。
*   **指令**：同時設定 `journal_mode=WAL` 與 `synchronous=NORMAL`。
*   **理由**：這是 aiosqlite 環境下最穩健的做法，確保每個連線都正確掛載效能參數。

### B. 目錄結構
```text
server/app/
├── api/             # 櫃檯：負責路由與資料處理邏輯
├── models/          # 藍圖：SQLAlchemy 資料表定義
│   └── __init__.py  # 自動註冊中心
├── schemas/         # 安檢：Pydantic 資料格式定義
├── security/        # 工具：HASHER, JWT, OTP (已就位)
├── database.py      # 基礎設施：連線池與 SQLite 參數優化
└── main.py          # 總控：負責生命週期 (lifespan) 與路由掛載
```

## 3. 實作步驟 (Action Items)

### Step 1: 基礎設施清理 (database.py & main.py)
*   **`database.py`**：補上 `PRAGMA synchronous=NORMAL`。
*   **`main.py`**：**徹底移除** 所有的 `PRAGMA` 相關程式碼，僅保留建表邏輯。

### Step 2: 模型層整頓 (models/)
*   建立 `app/models/__init__.py`，匯入 `User`。
*   修改 `main.py`，改為 `import app.models`。

### Step 3: Schema 抽離 (schemas/)
*   建立 `app/schemas/auth.py`。
*   將登入與驗證相關的 Pydantic 模型搬移過去，並在 `api/auth.py` 中引用。

### Step 4: 全面 Package 化 (Package Optimization)
*   **目標**：補齊所有子目錄的 `__init__.py` 並進行顯式導出。
*   **具體動作**：
    *   `app/api/__init__.py`: 加入 `from . import auth`
    *   `app/security/__init__.py`: 加入 `from . import hasher, jwt, otp`
    *   `app/middleware/__init__.py`: 加入 `from . import real_ip`
    *   `app/core/__init__.py`: 加入 `from . import config`
*   **為什麼要這樣改？**
    1.  **防止 AttributeError**：解決 `module 'app.xxx' has no attribute 'yyy'` 的問題。Python 預設不會在匯入資料夾時自動加載子檔案，顯式導出能確保子模組隨 Package 一起就緒。
    2.  **解耦檔案路徑**：`__init__.py` 扮演了「分線器」的角色。未來即使我們把 `hasher.py` 拆成多個檔案，只要在 `__init__.py` 窗口維持同樣的匯出，外部引用者（如 `auth.py`）就不需要改動程式碼。
    3.  **符合企業級標準**：這是大型專案維持結構穩健、降低匯入錯誤的標準實踐。

---
