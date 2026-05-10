from fastapi import APIRouter
from .auth import router as auth_router

# 建立總路由物件
api_router = APIRouter()

# 匯總所有子模組路由
# prefix="/auth" 代表之後所有的路徑都會是 /api/auth/...
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# 未來可以在這裡輕鬆擴充新的功能：
# from .files import router as files_router
# api_router.include_router(files_router, prefix="/files", tags=["files"])
