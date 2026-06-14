"""
應用程式主入口 (Main Entry Point)
職責：
1. 初始化 FastAPI 實例與生命週期管理 (Lifespan)
2. 註冊 Middleware (警衛)
3. 掛載 API 路由 (專櫃)
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from app.core.database import init_db
from app.core.cache import init_redis, close_redis
from app.gc.sentinel import run_gc_sentinel
from app.middleware import RealIPMiddleware
from app.api import api_router # 匯入總路由
from starlette.middleware import Middleware
from app.core.exceptions import BaseBusinessException, business_exception_handler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時：透過封裝好的函式初始化資料庫
    await init_db()
    
    # 啟動時：初始化 Redis 快取連線池 (Fail-fast)
    await init_redis()
    
    # 啟動時：建立並拉起背景垃圾回收定時哨兵任務
    gc_task = asyncio.create_task(run_gc_sentinel())
    app.state.gc_task = gc_task
    
    yield
    
    # 關閉時：優雅取消背景任務，防止資源與協程洩漏
    if hasattr(app.state, "gc_task"):
        app.state.gc_task.cancel()
        try:
            await app.state.gc_task
        except asyncio.CancelledError:
            pass
            
    # 關閉時：優雅釋放 Redis 連線池
    await close_redis()


app = FastAPI(
    title="File Explorer",
    lifespan=lifespan,
    # 1. 整合 Middleware
    middleware=[
        Middleware(RealIPMiddleware)
    ],
    # 2. 整合 全域異常處理器
    exception_handlers={
        BaseBusinessException: business_exception_handler
    }
)

# 3. 註冊 API 路由 (統一掛載在 /api 之下)
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Secure File Explorer API is running"}

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
