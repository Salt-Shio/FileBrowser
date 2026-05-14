"""
核心異常模組 (Core Exceptions)
職責：
1. 定義全域業務邏輯異常類別 (Business Exceptions)
2. 提供 FastAPI 異常處理器的統一註冊入口
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class BaseBusinessException(Exception):
    """
    所有業務異常的基類
    """
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class NodeNotFoundError(BaseBusinessException):
    """
    找不到檔案或資料夾
    """
    def __init__(self, message: str = "找不到指定的物件"):
        super().__init__(message, status_code=404)

class DuplicateNodeError(BaseBusinessException):
    """
    名稱衝突（例如同目錄下已有同名檔案）
    """
    def __init__(self, message: str = "名稱已存在"):
        super().__init__(message, status_code=400)

class PermissionDeniedError(BaseBusinessException):
    """
    權限不足
    """
    def __init__(self, message: str = "權限不足，無法執行此操作"):
        super().__init__(message, status_code=403)

class AuthenticationError(BaseBusinessException):
    """
    身分驗證失敗 (例如密碼錯誤、2FA 錯誤)
    """
    def __init__(self, message: str = "身分驗證失敗"):
        super().__init__(message, status_code=401)

class InvalidTokenError(BaseBusinessException):
    """
    Token 無效或已過期
    """
    def __init__(self, message: str = "憑證無效或已過期，請重新登入"):
        super().__init__(message, status_code=401)


async def business_exception_handler(request: Request, exc: BaseBusinessException):
    """
    統一處理所有繼承自 BaseBusinessException 的異常
    將其轉換為標準的 JSON 錯誤回應
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.__class__.__name__
        }
    )

def setup_exception_handlers(app: FastAPI):
    """
    (舊版相容) 在 FastAPI App 中註冊全域異常處理器
    """
    app.add_exception_handler(BaseBusinessException, business_exception_handler)
