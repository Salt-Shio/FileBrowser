"""
應用程式主入口 (Main Entry Point)
職責：
1. 初始化 FastAPI 實例與生命週期管理 (Lifespan)
2. 註冊 Middleware (警衛)
3. 掛載 API 路由 (專櫃)
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db
from app.middleware import RealIPMiddleware
from app.api import api_router # 匯入總路由

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時：透過封裝好的函式初始化資料庫
    await init_db()
    yield

app = FastAPI(
    title="File Explorer",
    lifespan=lifespan
)

# 1. 註冊 Middleware
app.add_middleware(RealIPMiddleware)

# 2. 註冊 API 路由 (統一掛載在 /api 之下)
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Secure File Explorer API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
