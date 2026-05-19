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
    async def register(db: AsyncSession, username: str, password: str):
        """
        註冊新使用者
        """
        # 1. 檢查帳號是否已存在
        # TODO: 這裡後續可能會補上白名單機制，畢竟是單人專用
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalars().first()
        if existing_user:
            from app.core.exceptions import BaseBusinessException
            raise BaseBusinessException("該帳號已被註冊", status_code=400)
            
        # 2. 加密密碼
        hashed_password = hasher.get_password_hash(password)
        
        # 3. 建立使用者物件 (2FA 預設為 False)
        user = User(
            username=username,
            hashed_password=hashed_password,
            is_totp_enabled=False,
            totp_secret=None
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user

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
        
        # 3. 根據是否啟用 2FA 決定流程
        if user.is_totp_enabled:
            # 簽發 2FA 短效憑證
            two_fa_token = jwt.create_2fa_token(user.username)
            return {
                "message": "密碼驗證成功，請輸入 2FA 驗證碼",
                "require_2fa": True,
                "two_fa_token": two_fa_token,
                "username": user.username
            }
        else:
            # 直接簽發正式 JWT access_token
            access_token = jwt.create_access_token(data={"sub": user.username})
            return {
                "message": "登入成功",
                "require_2fa": False,
                "access_token": access_token,
                "token_type": "bearer",
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

    @staticmethod
    async def generate_2fa_setup(db: AsyncSession, username: str):
        """
        為已登入的使用者產生新的 2FA 安全金鑰與 URI
        """
        # 1. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if not user:
            from app.core.exceptions import NodeNotFoundError
            raise NodeNotFoundError("使用者不存在")

        if user.is_totp_enabled:
            from app.core.exceptions import BaseBusinessException
            raise BaseBusinessException("已啟用 2FA，若要重新綁定請先停用舊的 2FA", status_code=400)

        # 2. 產生金鑰
        secret = otp.generate_otp_secret()
        
        # 3. 暫存至資料庫 (is_totp_enabled 保持 False，防範鎖定)
        user.totp_secret = secret
        user.is_totp_enabled = False
        await db.commit()
        await db.refresh(user)
        
        # 4. 取得 URI
        uri = otp.get_provisioning_uri(user.username, secret)
        
        return {
            "secret": secret,
            "provisioning_uri": uri
        }

    @staticmethod
    async def enable_2fa(db: AsyncSession, username: str, otp_code: str):
        """
        驗證首次 2FA 代碼，正式啟用 2FA 功能
        """
        # 1. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if not user:
            from app.core.exceptions import NodeNotFoundError
            raise NodeNotFoundError("使用者不存在")

        if not user.totp_secret:
            from app.core.exceptions import BaseBusinessException
            raise BaseBusinessException("請先請求產生 2FA 金鑰", status_code=400)
            
        # 驗證 OTP 驗證碼
        if not otp.verify_otp_code(user.totp_secret, otp_code):
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError("2FA 驗證碼錯誤或已過期")
            
        # 驗證成功，正式開啟 2FA 開關
        user.is_totp_enabled = True
        await db.commit()
        await db.refresh(user)
        
        return {"message": "2FA 啟用成功"}

    @staticmethod
    async def disable_2fa(db: AsyncSession, username: str, otp_code: str):
        """
        驗證當前 2FA 代碼，停用 2FA 功能
        """
        # 1. 尋找使用者
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if not user:
            from app.core.exceptions import NodeNotFoundError
            raise NodeNotFoundError("使用者不存在")

        if not user.is_totp_enabled or not user.totp_secret:
            from app.core.exceptions import BaseBusinessException
            raise BaseBusinessException("使用者尚未啟用 2FA", status_code=400)
            
        # 驗證 OTP 驗證碼
        if not otp.verify_otp_code(user.totp_secret, otp_code):
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError("2FA 驗證碼錯誤或已過期")
            
        # 驗證成功，停用 2FA 並清除金鑰
        user.is_totp_enabled = False
        user.totp_secret = None
        await db.commit()
        await db.refresh(user)
        
        return {"message": "2FA 停用成功"}

