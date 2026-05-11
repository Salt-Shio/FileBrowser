"""
虛擬檔案系統服務 (VFS Service)
職責：
1. 處理資料夾與檔案的 CRUD 核心業務邏輯
2. 實作導航核心 (UUID 查詢與麵包屑生成)
3. 確保所有操作皆符合擁有者權限驗證 (Security)
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.vfs import Folder, File
from app.schemas.vfs import Breadcrumb

class VFSService:
    """
    虛擬檔案系統服務 (VFS Service)
    職責：處理檔案與目錄的 CRUD 業務邏輯，並確保資料安全與一致性。
    """

    @staticmethod
    async def get_folder_by_id(db: AsyncSession, folder_id: str, owner_id: str) -> Optional[Folder]:
        """
        根據 UUID 獲取資料夾，並驗證擁有者與刪除狀態。
        """
        stmt = select(Folder).where(
            Folder.id == folder_id,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_file_by_id(db: AsyncSession, file_id: str, owner_id: str) -> Optional[File]:
        """
        根據 UUID 獲取檔案，並驗證擁有者與刪除狀態。
        """
        stmt = select(File).where(
            File.id == file_id,
            File.owner_id == owner_id,
            File.is_deleted == False
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_breadcrumbs(db: AsyncSession, folder_id: Optional[str], owner_id: str) -> List[Breadcrumb]:
        """
        生成從根目錄到指定目錄的麵包屑路徑。
        """
        breadcrumbs = []
        current_id = folder_id

        while current_id:
            folder = await VFSService.get_folder_by_id(db, current_id, owner_id)
            if folder is None:
                break
            
            # 插入到清單最前面 (因為我們是從下往上找)
            breadcrumbs.insert(0, Breadcrumb(id=folder.id, name=folder.name))
            
            # 往上一層
            current_id = folder.parent_id

        return breadcrumbs
