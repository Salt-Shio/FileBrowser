"""
上傳管理模型 (Upload Models)
職責：
1. 定義 upload_sessions 資料表，追蹤分塊傳輸狀態
2. 提供物理碎片與使用者身分的關聯校驗
3. 作為結算工作流 (Finalization) 的核心依據
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class UploadSession(Base):
    """
    上傳會話模型 (Upload Session Model)
    職責：管理分塊上傳的中間狀態，確保實體優先原則與身分安全性。
    """
    __tablename__ = "upload_sessions"

    # 1. 唯一會話識別碼 (作為 upload_id)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 2. 擁有者 (用於 IDOR 防護，確保只有本人能續傳碎片)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # 3. 原始檔案資訊 (結算時用於入籍 VFS)
    filename = Column(String, nullable=False)
    target_folder_id = Column(String, ForeignKey("folders.id"), nullable=True)
    
    # 4. 分塊進度控管
    total_chunks = Column(Integer, nullable=False)
    
    # 5. 完整性預期 (SHA256，由前端提供)
    expected_hash = Column(String, nullable=True)
    
    # 6. 會話建立時間 (用於自動清理 GC 判定)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 關係設定
    # 與 User 建立雙向關係，符合 VFS 模組的嚴謹定義風格
    owner = relationship("User", back_populates="upload_sessions", foreign_keys=[owner_id])
