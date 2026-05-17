"""
管理員初始化腳本 (Admin Initialization Script) - 增強版
職責：
1. 建立首位管理員
2. [新增] 自動為管理員產生 2FA (TOTP) 金鑰
3. [新增] 輸出金鑰資訊，方便開發者進行手機綁定
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.security.hasher import get_password_hash
from app.security.otp import generate_otp_secret, get_provisioning_uri
from app.core.config import settings

async def init_admin():
    async with AsyncSessionLocal() as db:
        # 1. 檢查管理員是否已存在
        result = await db.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        user = result.scalars().first()

        if user and user.totp_secret:
            print(f"[*] 管理員 '{settings.ADMIN_USERNAME}' 已存在且已設定 2FA。")
            print(f"[*] 您的 2FA 金鑰為: {user.totp_secret}")
            return

        # 2. 如果使用者存在但沒金鑰，或是全新使用者
        if not user:
            print(f"[*] 正在建立管理員: {settings.ADMIN_USERNAME}...")
            hashed_pw = get_password_hash(settings.ADMIN_PASSWORD)
            user = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hashed_pw,
                is_active=True
            )
            db.add(user)
        
        # 3. 產生並設定 2FA 金鑰
        otp_secret = generate_otp_secret()
        user.totp_secret = otp_secret
        
        await db.commit()
        
        # 4. 輸出重要資訊
        print(f"\n" + "="*40)
        print(f"[+] 管理員 '{settings.ADMIN_USERNAME}' 設定成功！")
        print(f"[*] 請將以下金鑰輸入您的手機 App (如 Google Authenticator):")
        print(f"    金鑰 (Secret): {otp_secret}")
        print(f"    帳號名稱: {settings.ADMIN_USERNAME}")
        print(f"    發行者: {settings.APP_NAME}")
        print("-" * 40)
        
        # 額外提供 URI 連結 (可選)
        uri = get_provisioning_uri(settings.ADMIN_USERNAME, otp_secret)
        print(f"[*] 或是您可以複製此連結產生的 QR Code:")
        print(f"    {uri}")
        print("="*40 + "\n")

if __name__ == "__main__":
    asyncio.run(init_admin())
