"""
虛擬檔案系統模型 (VFS Data Models)
職責：
1. 定義 folders 與 files 資料表的欄位結構 (Schema)
2. 管理虛擬路徑的層級關係與檔案元數據
3. 建立虛擬節點與實體磁碟路徑的映射
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Folder(Base):
    """
    虛擬目錄模型 (Virtual Folder Model)
    職責：管理資料夾的層級結構與虛擬路徑。
    """
    __tablename__ = "folders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    
    # 父目錄關聯 (Root 目錄的 parent_id 為 Null)
    parent_id = Column(String, ForeignKey("folders.id"), nullable=True)
    
    # 擁有者關聯
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 時間戳記
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 狀態
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # 關係設定
    owner = relationship("User", back_populates="folders", foreign_keys=[owner_id])
    
    # 資料夾樹狀關係：parent 指向父目錄，subfolders 指向子目錄清單
    parent = relationship("Folder",  back_populates="subfolders",  foreign_keys=[parent_id], remote_side=[id])
    subfolders = relationship("Folder", back_populates="parent", foreign_keys=[parent_id])
    
    files = relationship("File", back_populates="folder", foreign_keys="[File.folder_id]")

    # 索引：優化目錄列出效能 (owner + parent 的組合查詢)
    # 存的時候 binary insert (犧牲存入的性能)
    # 找的時候 binary search (找的使用頻率 >> 存入)
    __table_args__ = (
        Index("idx_folder_owner_parent", "owner_id", "parent_id"),
    )



class File(Base):
    """
    虛擬檔案模型 (Virtual File Model)
    職責：記錄檔案元數據與實體儲存路徑的映射。
    """
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    
    # 所屬目錄
    folder_id = Column(String, ForeignKey("folders.id"), nullable=True)
    
    # 擁有者
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 檔案屬性
    size = Column(BigInteger, default=0)
    mime_type = Column(String, nullable=True)
    
    # 實體儲存資訊
    storage_path = Column(String, nullable=False)
    hash_sha256 = Column(String, index=True, nullable=False)
    
    # 時間與狀態
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # 關係設定
    folder = relationship("Folder", back_populates="files", foreign_keys=[folder_id])
    owner = relationship("User", back_populates="files", foreign_keys=[owner_id])

    # 索引：優化檔案查詢
    __table_args__ = (
        Index("idx_file_folder_owner", "folder_id", "owner_id"),
    )
