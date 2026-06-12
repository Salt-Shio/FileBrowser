"""
使用者資料模型 (User Data Model)
職責：
1. 定義 users 資料表的欄位結構 (Schema)
2. 設定欄位約束 (如 Unique, Index)
3. 作為 SQLAlchemy ORM 操作的物件實體
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    # 1. 唯一識別碼 (使用 UUID 字串)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 2. 帳號 (唯一且建立索引，方便快速搜尋)
    username = Column(String, unique=True, index=True, nullable=False)
    
    # 3. 攪碎後的密碼 (Argon2 雜湊字串)
    hashed_password = Column(String, nullable=False)
    
    # 4. 2FA 安全金鑰 (初始為空，啟用後才填入)
    totp_secret = Column(String, nullable=True)
    
    # 5. 是否已啟用 2FA 開關
    is_totp_enabled = Column(Boolean, default=False)
    
    # 6. 帳號狀態
    is_active = Column(Boolean, default=True)
    
    # 7. 建立時間
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # VFS 關聯
    folders = relationship("Folder", back_populates="owner", foreign_keys="[Folder.owner_id]")
    files = relationship("File", back_populates="owner", foreign_keys="[File.owner_id]")
    upload_sessions = relationship("UploadSession", back_populates="owner", foreign_keys="[UploadSession.owner_id]")
