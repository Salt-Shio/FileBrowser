"""
身分驗證 API 路由 (Authentication Endpoints)
職責：
1. 處理使用者登入 (密碼驗證)
2. 處理雙重驗證 (2FA 驗證)
3. 簽發 JWT 通行證
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.auth_service import AuthService
from app import schemas

router = APIRouter()

# --- API 實作 ---

@router.post("/login")
async def login(data: schemas.auth.LoginRequest, db: AsyncSession = Depends(deps.get_db)):
    """
    第一階段：密碼驗證
    """
    return await AuthService.login(db, data)

@router.post("/verify-2fa")
async def verify_2fa(data: schemas.auth.Verify2FARequest, db: AsyncSession = Depends(deps.get_db)):
    """
    第二階段：2FA 驗證與簽發 JWT
    """
    return await AuthService.verify_2fa(db, data)
