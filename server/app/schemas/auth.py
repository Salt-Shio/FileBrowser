"""
認證相關數據模型 (Auth Schemas)
職責：
1. 定義登入、2FA 驗證等請求的輸入結構
2. 進行身分驗證相關資料的初步驗證
"""
from pydantic import BaseModel

from typing import Optional

class LoginRequest(BaseModel):
    """
    登入請求模型
    """
    username: str
    password: str

class RegisterRequest(BaseModel):
    """
    註冊請求模型
    """
    username: str
    password: str

class Verify2FARequest(BaseModel):
    """
    2FA 驗證請求模型
    """
    two_fa_token: str
    otp_code: str

class LoginResponse(BaseModel):
    """
    登入第一階段回傳模型
    """
    message: str
    require_2fa: bool
    two_fa_token: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    username: str

class Generate2FAResponse(BaseModel):
    """
    產生 2FA 金鑰回傳模型
    """
    secret: str
    provisioning_uri: str

class VerifyOTPRequest(BaseModel):
    """
    驗證 OTP 驗證碼請求模型
    """
    otp_code: str

class ChangePasswordRequest(BaseModel):
    """
    更改密碼請求模型
    """
    old_password: str
    new_password: str
