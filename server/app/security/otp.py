"""
OTP 安全模組 (One-Time Password)
職責：
1. 產生隨機的 Base32 金鑰 (Secret Key)
2. 產生供手機掃描的 URI 連結 (otpauth)
3. 驗證使用者輸入的 6 位數 TOTP 驗證碼
4. [新增] 獲取目前的 6 位數代碼 (供內部測試使用)
"""
import pyotp
import time
from app.core.config import settings

def generate_otp_secret() -> str:
    """
    產生一個隨機的 Base32 金鑰
    """
    return pyotp.random_base32()

def get_provisioning_uri(username: str, secret: str) -> str:
    """
    產生供手機掃描的 QR Code 連結
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, 
        issuer_name=settings.APP_NAME
    )

def verify_otp_code(secret: str, code: str) -> bool:
    """
    驗證使用者輸入的 6 位數代碼是否正確
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def get_current_otp_code(secret: str) -> dict:
    """
    獲取目前的 6 位數代碼與剩餘秒數 (Debug 用)
    """
    totp = pyotp.TOTP(secret)
    remaining_seconds = 30 - (time.time() % 30)
    return {
        "code": totp.now(),
        "remaining": int(remaining_seconds)
    }

if __name__ == "__main__":
    # 自我測試邏輯
    s = generate_otp_secret()
    data = get_current_otp_code(s)
    print(f"Secret: {s}")
    print(f"Current Code: {data['code']} (valid for {data['remaining']}s)")
    print(f"Verify: {verify_otp_code(s, data['code'])}")
