# 系統程式架構圖 (System Structure Diagram)

本圖表呈現以 `app.main` 為核心的調用階層與模組關係。

```mermaid
graph TD
    subgraph Layer_1 [管理層 - 入口]
        MAIN["main.py (入口點)"]
        MIDDLEWARE["middleware/ (攔截器)"]
        CORE["core/config.py (系統配置)"]
        API_INIT["api/__init__.py (總路由)"]
        GC_SENTINEL["gc/sentinel.py (垃圾回收哨兵)"]
    end

    subgraph Layer_2 [介面層 - Router]
        AUTH_API["api/auth.py (身分驗證)"]
        VFS_API["api/vfs.py (檔案系統)"]
    end

    subgraph Layer_3 [執行層 - Service & Deps]
        AUTH_SVC["services/auth_service.py (身分業務)"]
        VFS_SVC["services/vfs_service.py (檔案業務)"]
        DEPS["api/deps.py (依賴注入中心)"]
    end

    subgraph Layer_4 [基礎層 - Security & Data]
        JWT["security/jwt.py"]
        HASHER["security/hasher.py"]
        OTP["security/otp.py"]
        DB[("database.py / DB")]
        MODELS["models/ (資料結構)"]
        SCHEMAS["schemas/ (Pydantic)"]
    end

    %% 調用關係
    MAIN --> MIDDLEWARE
    MAIN --> CORE
    MAIN --> API_INIT
    MAIN --> GC_SENTINEL

    API_INIT --> AUTH_API
    API_INIT --> VFS_API

    %% 業務與依賴
    AUTH_API --> AUTH_SVC
    AUTH_API --> DEPS
    VFS_API --> VFS_SVC
    VFS_API --> DEPS

    %% 執行層調用基礎層
    AUTH_SVC --> JWT
    AUTH_SVC --> HASHER
    AUTH_SVC --> OTP
    AUTH_SVC --> DB
    AUTH_SVC --> MODELS

    VFS_SVC --> DB
    VFS_SVC --> MODELS
    VFS_SVC --> JWT

    DEPS --> DB
    DEPS --> JWT
    DEPS --> MODELS

    %% 背景 GC 哨兵調用
    GC_SENTINEL --> DB

    %% Schema 調用
    AUTH_API -.-> SCHEMAS
    VFS_API -.-> SCHEMAS

    %% 樣式美化
    style MAIN fill:#FF9800,stroke:#333,stroke-width:4px,color:#000
    style GC_SENTINEL fill:#FF9800,stroke:#333,stroke-width:2px,color:#000
    style API_INIT fill:#2196F3,stroke:#333,stroke-width:2px,color:#fff
    style AUTH_SVC fill:#C8E6C9,stroke:#333,stroke-width:2px,color:#000
    style VFS_SVC fill:#C8E6C9,stroke:#333,stroke-width:2px,color:#000
    style DB fill:#ECEFF1,stroke:#333,color:#000
```

---

## 核心層級說明

1.  **管理層 (Top)**：`main.py` 負責將所有模組組裝起來。在應用啟動時，它會拉起背景垃圾回收哨兵 (`app/gc/sentinel.py`) 任務；並在應用關閉時，優雅地取消該哨兵，避免資源洩漏。
2.  **路由層 (Router)**：`api/` 負責分流外部 HTTP 請求，但不處理複雜邏輯。
3.  **依賴層 (Deps)**：`deps.py` 像是一個橋樑，把底層的「資料庫」與「安全工具」提供給上層。
4.  **執行層 (Logic)**：`services/` 才是真正動手處理資料的地方。
5.  **基礎層 (Base)**：`models`, `database`, `security` 是最純粹的工具，不依賴任何人。
