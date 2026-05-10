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
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/data/uploads")
    
    # 初始管理員 (Step 1.3 會用到)
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD")

    class Config:
        case_sensitive = True

# 實例化供全域使用
settings = Settings()
