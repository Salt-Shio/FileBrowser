"""
VFS 數據傳輸模型 (VFS Schemas)
職責：
1. 定義 API 輸入與輸出的資料結構 (Pydantic Models)
2. 進行資料型別驗證與轉換
3. 提供前端導航所需的 Breadcrumb 結構
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Breadcrumb(BaseModel):
    """
    路徑麵包屑模型
    """
    id: str
    name: str

class FolderBase(BaseModel):
    """
    資料夾基礎模型
    """
    name: str
    parent_id: Optional[str] = None

class FolderCreate(FolderBase):
    """
    建立資料夾時的輸入模型
    """
    pass

class FolderResponse(FolderBase):
    """
    資料夾回傳模型 (包含系統產生的欄位)
    """
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    # 可以轉 JSON
    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    """
    檔案回傳模型
    """
    id: str
    name: str
    folder_id: Optional[str]
    owner_id: str
    size: int
    mime_type: Optional[str]
    hash_sha256: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BrowseResponse(BaseModel):
    """
    瀏覽目錄回傳模型
    """
    current_folder: FolderResponse
    breadcrumbs: List[Breadcrumb]
    subfolders: List[FolderResponse]
    files: List[FileResponse]

class SearchResponse(BaseModel):
    """
    搜尋結果回傳模型
    """
    folders: List[FolderResponse]
    files: List[FileResponse]

class NodeRenameRequest(BaseModel):
    """
    節點更名請求模型 (支援檔案與資料夾)
    """
    node_id: str
    node_type: str  # "file" 或 "folder"
    new_name: str
