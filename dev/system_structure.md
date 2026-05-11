# 系統程式架構圖 (System Structure Diagram)

本圖表呈現以 `app.main` 為核心的調用階層與模組關係。

```mermaid
graph TD
    %% 頂層入口
    MAIN["main.py (入口點)"]

    %% 中間層
    API_INIT["api/__init__.py (總路由)"]
    MIDDLEWARE["middleware/ (攔截器)"]
    CORE["core/config.py (系統配置)"]

    %% 業務分流層
    AUTH_API["api/auth.py (身分驗證)"]
    VFS_API["api/vfs.py (檔案系統)"]

    %% 依賴與邏輯層
    DEPS["api/deps.py (依賴注入中心)"]
    VFS_SVC["services/vfs_service.py (業務邏輯)"]

    %% 底層工具與資料
    JWT["security/jwt.py (權杖工具)"]
    HASHER["security/hasher.py (密碼工具)"]
    MODELS["models/ (資料結構)"]
    DB["database.py (資料庫連線)"]
    SCHEMAS["schemas/ (資料規範)"]

    %% 調用關係
    MAIN --> MIDDLEWARE
    MAIN --> CORE
    MAIN --> API_INIT

    API_INIT --> AUTH_API
    API_INIT --> VFS_API

    %% API 依賴關係
    AUTH_API --> DEPS
    VFS_API --> DEPS
    VFS_API --> VFS_SVC

    %% 依賴注入的流向
    DEPS --> DB
    DEPS --> JWT
    DEPS --> MODELS

    %% Service 的流向
    VFS_SVC --> DB
    VFS_SVC --> MODELS
    VFS_SVC --> JWT

    %% 跨模組工具
    AUTH_API --> HASHER
    AUTH_API --> SCHEMAS
    VFS_API --> SCHEMAS

    %% 樣式美化 (高對比度配色)
    style MAIN fill:#FF9800,stroke:#333,stroke-width:4px,color:#000
    style API_INIT fill:#2196F3,stroke:#333,stroke-width:2px,color:#fff
    style AUTH_API fill:#90CAF9,stroke:#333,color:#000
    style VFS_API fill:#90CAF9,stroke:#333,color:#000
    style DEPS fill:#E1BEE7,stroke:#333,stroke-dasharray: 5 5,color:#000
    style VFS_SVC fill:#C8E6C9,stroke:#333,stroke-width:2px,color:#000
    style JWT fill:#ECEFF1,stroke:#333,color:#000
    style HASHER fill:#ECEFF1,stroke:#333,color:#000
    style MODELS fill:#ECEFF1,stroke:#333,color:#000
    style DB fill:#ECEFF1,stroke:#333,color:#000
    style SCHEMAS fill:#ECEFF1,stroke:#333,color:#000
```

---

## 核心層級說明

1.  **管理層 (Top)**：`main.py` 負責將所有模組組裝起來。
2.  **路由層 (Router)**：`api/` 負責分流請求，但不處理複雜邏輯。
3.  **依賴層 (Deps)**：`deps.py` 像是一個橋樑，把底層的「資料庫」與「安全工具」提供給上層。
4.  **執行層 (Logic)**：`services/` 才是真正動手處理資料的地方。
5.  **基礎層 (Base)**：`models`, `database`, `security` 是最純粹的工具，不依賴任何人。
