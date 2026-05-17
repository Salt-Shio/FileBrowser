"""
管理員 OTP 產生器 (Debug Tool)
職責：
透過引用系統內部的 otp 模組，獲取目前管理員的驗證碼。
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.security import otp
from app.core.config import settings

async def get_admin_otp():
    async with AsyncSessionLocal() as db:
        # 1. 抓取管理員
        result = await db.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        user = result.scalars().first()
        
        if not user or not user.totp_secret:
            print("[!] 找不到管理員或尚未設定 2FA，請先執行 python -m scripts.init_admin")
            return

        # 2. 呼叫系統內部的 otp 模組
        otp_data = otp.get_current_otp_code(user.totp_secret)
        
        print(f"\n" + "="*30)
        print(f"[*] 管理員: {user.username}")
        print(f"[*] 目前的 6 位數密碼: {otp_data['code']}")
        print(f"[*] 剩餘秒數: {otp_data['remaining']}s")
        print("="*30 + "\n")

if __name__ == "__main__":
    asyncio.run(get_admin_otp())
