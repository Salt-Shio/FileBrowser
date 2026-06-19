"""
Redis 快取配置模組 (Redis Configuration)
職責：
1. 管理 Redis 連線池與初始化 (Singleton Pattern)
2. 啟動時檢查連線可用性 (Fail-fast)
3. 提供應用關閉時優雅釋放資源的方法
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import settings

class RedisManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self) -> redis.Redis:
        """
        安全獲取 Redis 客戶端
        若尚未初始化，則拋出明確例外，避免隱晦的 NoneType Error
        """
        if self._client is None:
            raise RuntimeError("Redis client is not initialized. Call init_pool() first.")
        return self._client

    async def init_pool(self):
        """
        初始化 Redis 連線池，採用 Fail-fast 策略。
        如果在啟動期間無法連線至 Redis，直接拋出例外終止服務。
        """
        try:
            pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=pool)
            await self._client.ping()
            print("Redis connection pool initialized successfully.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to connect to Redis at {settings.REDIS_URL}.")
            print(f"Error details: {str(e)}")
            raise RuntimeError("Redis initialization failed. System cannot start.") from e

    async def close_pool(self):
        """
        優雅關閉 Redis 連線池。
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            print("Redis connection pool closed gracefully.")

# 單例匯出
redis_manager = RedisManager()
