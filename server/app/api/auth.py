"""
身分驗證 API 路由 (Authentication Endpoints)
職責：
1. 處理使用者登入 (密碼驗證)
2. 處理雙重驗證 (2FA 驗證)
3. 簽發 JWT 通行證
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.auth_service import AuthService
from app.models import User
from app import schemas



router = APIRouter()

# --- API 實作 ---

@router.post("/register", response_model=schemas.user.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: schemas.auth.RegisterRequest, db: AsyncSession = Depends(deps.get_db)):
    """
    使用者註冊端點
    """
    return await AuthService.register(db, data.username, data.password)

@router.post("/login", response_model=schemas.auth.LoginResponse)
async def login(data: schemas.auth.LoginRequest, db: AsyncSession = Depends(deps.get_db)):
    """
    第一階段：密碼驗證
    """
    return await AuthService.login(db, data.username, data.password)

@router.post("/verify-2fa", response_model=schemas.user.Token)
async def verify_2fa(
    data: schemas.auth.Verify2FARequest,
    db: AsyncSession = Depends(deps.get_db),
    redis_client = Depends(deps.get_redis)
):
    """
    第二階段：2FA 驗證與簽發 JWT
    """
    return await AuthService.verify_2fa(db, redis_client, data.two_fa_token, data.otp_code)

@router.get("/me", response_model=schemas.user.UserResponse)
async def get_me(current_user: User = Depends(deps.get_current_user)):
    """
    獲取當前登入使用者資訊 (展示 Schema 過濾密碼的功能)
    """
    return current_user

@router.post("/2fa/generate", response_model=schemas.auth.Generate2FAResponse)
async def generate_2fa(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    產生 2FA 金鑰與二維碼
    """
    return await AuthService.generate_2fa_setup(db, current_user.username)

@router.post("/2fa/enable")
async def enable_2fa(
    data: schemas.auth.VerifyOTPRequest,
    db: AsyncSession = Depends(deps.get_db),
    redis_client = Depends(deps.get_redis),
    current_user: User = Depends(deps.get_current_user)
):
    """
    驗證首次 2FA 碼並正式啟用 2FA 功能
    """
    return await AuthService.enable_2fa(db, redis_client, current_user.username, data.otp_code)

@router.post("/2fa/disable")
async def disable_2fa(
    data: schemas.auth.VerifyOTPRequest,
    db: AsyncSession = Depends(deps.get_db),
    redis_client = Depends(deps.get_redis),
    current_user: User = Depends(deps.get_current_user)
):
    """
    驗證當前 2FA 碼並正式停用 2FA 功能
    """
    return await AuthService.disable_2fa(db, redis_client, current_user.username, data.otp_code)

@router.post("/change-password")
async def change_password(
    data: schemas.auth.ChangePasswordRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    修改密碼
    """
    return await AuthService.change_password(
        db, current_user.username, data.old_password, data.new_password
    )
