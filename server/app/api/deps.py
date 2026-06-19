"""
API 依賴項模組 (API Dependencies)
職責：
1. 集中管理所有 FastAPI 注入依賴項 (Depends)
2. 實作身分驗證與權限檢查邏輯
3. 整合 JWT 驗證與資料庫查詢
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from typing import AsyncGenerator
import redis.asyncio as redis
from app.core.database import AsyncSessionLocal
from app.models import User
from app.security import jwt

# 改用 HTTPBearer，這會讓 Swagger UI 出現一個純粹貼 Token 的輸入框
security = HTTPBearer()

async def get_db():
    """
    依賴注入用：獲取資料庫會話
    """
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    auth: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    驗證 Token 並回傳目前登入的使用者物件。
    """
    token = auth.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="身分驗證失敗，請重新登入",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. 解碼 Token
    payload = jwt.decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
    
    # 2. 提取使用者名稱 (sub)
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # 3. 從資料庫查詢該使用者
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    依賴注入用：獲取 Redis 客戶端實例。
    因為 redis.Redis(connection_pool=pool) 本身是執行緒安全且透過底層 Pool 借用連線，
    直接 yield 單例的 client 即可，不需要每次建立/關閉連線。
    """
    from app.core.cache import redis_manager
    try:
        client = redis_manager.client
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis service is unavailable."
        )
    yield client
