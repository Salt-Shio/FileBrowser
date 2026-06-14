"""
設定管理模組 (Configuration Management)
職責：
1. 讀取並驗證 .env 環境變數
2. 提供全域統一的 Settings 物件
3. 確保設定值的型別安全 (Type Safety)
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

class Settings(BaseSettings):
    # 基本設定
    APP_NAME: str = os.getenv("APP_NAME", "FileExplorer")
    
    # 安全設定
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    
    # 資料庫與存儲
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/data/uploads")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/app/data/temp")
    
    # 初始管理員 (Step 1.3 會用到)
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD")

    # 背景垃圾回收 (GC) 設定
    UPLOAD_SESSION_EXPIRE_HOURS: int = int(os.getenv("UPLOAD_SESSION_EXPIRE_HOURS", 24))
    GC_INTERVAL_SECONDS: int = int(os.getenv("GC_INTERVAL_SECONDS", 3600))

    # Uvicorn 伺服器設定
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))

    # Redis 連線設定
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))

    # 下載憑證相關參數 (VFS Download Ticket)
    DOWNLOAD_TICKET_TTL: int = int(os.getenv("DOWNLOAD_TICKET_TTL", 30))
    DOWNLOAD_TICKET_MAX_REQUESTS: int = int(os.getenv("DOWNLOAD_TICKET_MAX_REQUESTS", 4))

    # 檔案合併讀取緩衝區大小 (Byte，預設為 1MB)
    FILE_MERGE_BUFFER_SIZE: int = int(os.getenv("FILE_MERGE_BUFFER_SIZE", 1048576))

    # 2FA 綁定臨時權杖有效期限 (分鐘)
    TWO_FA_SETUP_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TWO_FA_SETUP_TOKEN_EXPIRE_MINUTES", 5))

    # 2FA 重放防禦快取時效 (秒)
    TWO_FA_REPLAY_TTL: int = int(os.getenv("TWO_FA_REPLAY_TTL", 60))

    class Config:
        case_sensitive = True

# 實例化供全域使用
settings = Settings()
