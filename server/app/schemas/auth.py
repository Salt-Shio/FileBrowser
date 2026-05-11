"""
認證相關數據模型 (Auth Schemas)
職責：
1. 定義登入、2FA 驗證等請求的輸入結構
2. 進行身分驗證相關資料的初步驗證
"""
from pydantic import BaseModel

class LoginRequest(BaseModel):
    """
    登入請求模型
    """
    username: str
    password: str

class Verify2FARequest(BaseModel):
    """
    2FA 驗證請求模型
    """
    username: str
    otp_code: str
