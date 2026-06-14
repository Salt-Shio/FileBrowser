"""
Redis 快取配置模組 (Redis Configuration)
職責：
1. 管理 Redis 連線池與初始化
2. 啟動時檢查連線可用性 (Fail-fast)
3. 提供應用關閉時優雅釋放資源的方法
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import settings

# 全域 Redis 客戶端實例
redis_client: Optional[redis.Redis] = None

async def init_redis():
    """
    初始化 Redis 連線池，採用 Fail-fast 策略。
    如果在啟動期間無法連線至 Redis，直接拋出例外終止服務。
    """
    global redis_client
    try:
        # 建立連線池 (設定 max_connections 由 settings 讀取)
        pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True # 自動將回傳值解碼為字串
        )
        redis_client = redis.Redis(connection_pool=pool)
        
        # 嘗試 ping，確認 Redis 存活 (Fail-fast)
        await redis_client.ping()
        print("Redis connection pool initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to connect to Redis at {settings.REDIS_URL}.")
        print(f"Error details: {str(e)}")
        raise RuntimeError("Redis initialization failed. System cannot start.") from e

async def close_redis():
    """
    優雅關閉 Redis 連線池。
    """
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        print("Redis connection pool closed gracefully.")
