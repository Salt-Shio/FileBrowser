"""
身分驗證 API 路由 (Authentication Endpoints)
職責：
1. 處理使用者登入 (密碼驗證)
2. 處理雙重驗證 (2FA 驗證)
3. 簽發 JWT 通行證
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.models import User
from app.security import hasher, otp, jwt
from app import schemas

router = APIRouter()

# --- API 實作 ---

@router.post("/login")
async def login(data: schemas.auth.LoginRequest, db: AsyncSession = Depends(deps.get_db)):
    """
    第一階段：密碼驗證
    """
    # 1. 尋找使用者
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalars().first()
    
    if not user or not hasher.verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤"
        )
    
    # 2. 密碼正確，通知前端需要進行 2FA 驗證
    return {
        "message": "密碼驗證成功，請輸入 2FA 驗證碼",
        "require_2fa": True,
        "username": user.username
    }

@router.post("/verify-2fa")
async def verify_2fa(data: schemas.auth.Verify2FARequest, db: AsyncSession = Depends(deps.get_db)):
    """
    第二階段：2FA 驗證與簽發 JWT
    """
    # 1. 尋找使用者獲取 TOTP Secret
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")
    
    # 2. 驗證 2FA 代碼
    if not otp.verify_otp_code(user.totp_secret, data.otp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA 驗證碼錯誤或已過期"
        )
    
    # 3. 全部通過，簽發正式 JWT
    access_token = jwt.create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }
