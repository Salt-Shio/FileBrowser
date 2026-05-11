"""
資料庫配置模組 (Database Configuration)
職責：
1. 初始化 SQLAlchemy 非同步引擎 (Async Engine)
2. 配置 SQLite 效能優化參數 (WAL 模式)
3. 提供資料庫初始化函式與會話供應器
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event
from .core.config import settings

# 1. 建立非同步資料庫引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# 2. SQLite 效能與併發優化
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # 開啟 WAL 模式：允許讀寫同時進行，解決 "Database is locked" 問題
    cursor.execute("PRAGMA journal_mode=WAL")
    # 設定同步等級：配合 WAL 模式，將安全性與速度平衡至最佳狀態
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# 3. 建立會話工廠 (Session Factory)
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 4. 定義模型基底類別
Base = declarative_base()

# 5. 資料庫初始化函式
async def init_db():
    """
    建立資料表並進行啟動前的最後準備
    """
    import app.models # 觸發所有模型的註冊
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
