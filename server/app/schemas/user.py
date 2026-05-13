"""
使用者數據傳輸模型 (User Schemas)
職責：
1. 定義使用者資訊的回傳結構 (UserResponse)
2. 定義 JWT Token 的結構 (Token)
3. 確保敏感資料（如密碼、2FA 金鑰）不會洩漏給前端
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """
    使用者基礎模型
    """
    username: str

class UserResponse(UserBase):
    """
    使用者資訊回傳模型 (出門模板)
    """
    id: str
    is_totp_enabled: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    """
    JWT 通行證模型
    """
    access_token: str
    token_type: str
    username: str  # 方便前端記錄當前使用者

class TokenPayload(BaseModel):
    """
    JWT Payload 解碼模型 (內部校驗用)
    """
    sub: Optional[str] = None
    exp: Optional[int] = None
