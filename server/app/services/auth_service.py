"""
身分驗證服務 (Auth Service)
職責：
1. 處理登入驗證流程
2. 處理 2FA 驗證流程
3. 協調 Security 工具與資料庫模型
"""
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
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError("帳號或密碼錯誤")
        
        # 3. 簽發 2FA 短效憑證
        two_fa_token = jwt.create_2fa_token(user.username)
        
        # 4. 返回驗證成功資訊
        return {
            "message": "密碼驗證成功，請輸入 2FA 驗證碼",
            "require_2fa": True,
            "two_fa_token": two_fa_token,
            "username": user.username
        }

    @staticmethod
    async def verify_2fa(db: AsyncSession, two_fa_token: str, otp_code: str):
        """
        第二階段：2FA 驗證與簽發 JWT
        """
        # 1. 解碼並驗證憑證 (業務層判斷 Policy)
        payload = jwt.decode_token(two_fa_token)
        if not payload or payload.get("type") != "2fa":
            from app.core.exceptions import InvalidTokenError
            raise InvalidTokenError("2FA 憑證無效或已過期，請重新登入")
        
        username = payload.get("sub")

        # 2. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        if not user:
            from app.core.exceptions import NodeNotFoundError
            raise NodeNotFoundError("使用者不存在")
        
        # 3. 驗證 2FA 代碼
        if not otp.verify_otp_code(user.totp_secret, otp_code):
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError("2FA 驗證碼錯誤或已過期")
        
        # 4. 簽發正式 JWT
        access_token = jwt.create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username
        }
