"""
身分驗證服務 (Auth Service)
職責：
1. 處理登入驗證流程
2. 處理 2FA 驗證流程
3. 協調 Security 工具與資料庫模型
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import User
from app.security import hasher, otp, jwt

class AuthService:
    """
    身分驗證業務邏輯層
    """

    @staticmethod
    async def login(db: AsyncSession, username: str, password: str):
        """
        第一階段：密碼驗證
        """
        # 1. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        # 2. 驗證密碼
        if not user or not hasher.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤"
            )
        
        # 3. 返回驗證成功資訊 (需要進行 2FA)
        return {
            "message": "密碼驗證成功，請輸入 2FA 驗證碼",
            "require_2fa": True,
            "username": user.username
        }

    @staticmethod
    async def verify_2fa(db: AsyncSession, username: str, otp_code: str):
        """
        第二階段：2FA 驗證與簽發 JWT
        """
        # 1. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="使用者不存在"
            )
        
        # 2. 驗證 2FA 代碼
        if not otp.verify_otp_code(user.totp_secret, otp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA 驗證碼錯誤或已過期"
            )
        
        # 3. 簽發正式 JWT
        access_token = jwt.create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username
        }
