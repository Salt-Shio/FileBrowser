"""
JWT 權杖管理模組 (JSON Web Token)
職責：
1. 簽發具有時效性的存取權杖 (Access Token)
2. 驗證權杖的合法性與是否過期
3. 解碼權杖內容以獲取使用者資訊
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings

# 從設定中讀取加密設定
ALGORITHM = settings.ALGORITHM

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    簽發一個新的 JWT 權杖
    data: 要放入 Payload 的資料 (例如 {"sub": "username"})
    """
    to_encode = data.copy()
    
    # 設定過期時間
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 預設過期時間 (從設定讀取)
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 注入 exp 與 type 欄位
    to_encode.update({"exp": expire, "type": "access"})
    
    # 使用 SECRET_KEY 進行簽名加密
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_2fa_token(username: str) -> str:
    """
    簽發一個極短效的 2FA 驗證憑證 (5 分鐘)
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {"sub": username, "exp": expire, "type": "2fa"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """
    解碼並驗證 JWT 權杖
    若驗證失敗或過期，則回傳 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # 包含過期、簽名錯誤等所有狀況
        return None
