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
    @staticmethod
    async def get_or_create_root(db: AsyncSession, owner_id: str) -> Folder:
        """
        獲取使用者的根目錄，如果不存在則自動建立一個。
        """
        # 1. 查詢 Root (parent_id 為 None 的資料夾)
        stmt = select(Folder).where(
            Folder.parent_id == None,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        )
        result = await db.execute(stmt)
        root = result.scalars().first()

        # 2. 如果不存在，則建立
        if root is None:
            root = Folder(
                name = "Root",
                parent_id = None,
                owner_id = owner_id
            )
            db.add(root)
            await db.commit()
            await db.refresh(root) 
            # 有些資料是 commit 後算的，所以需要 refresh 更新 root
        
        return root

    @staticmethod
    async def get_browse_data(db: AsyncSession, folder_id: str, owner_id: str):
        """
        整合查詢：獲取資料夾內容、檔案內容與麵包屑。
        """
        # 1. 獲取子資料夾
        folder_stmt = select(Folder).where(
            Folder.parent_id == folder_id,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        ).order_by(Folder.name.asc())
        folders_res = await db.execute(folder_stmt)
        folders = folders_res.scalars().all()

        # 2. 獲取子檔案
        file_stmt = select(File).where(
            File.folder_id == folder_id,
            File.owner_id == owner_id,
            File.is_deleted == False
        ).order_by(File.name.asc())
        files_res = await db.execute(file_stmt)
        files = files_res.scalars().all()

        # 3. 獲取麵包屑
        breadcrumbs = await VFSService.get_breadcrumbs(db, folder_id, owner_id)

        return {
            "folders": folders,
            "files": files,
            "breadcrumbs": breadcrumbs
        }

    @staticmethod
    async def search_nodes(db: AsyncSession, owner_id: str, query: str):
        """
        模糊搜尋使用者擁有的所有資料夾與檔案。
        """
        # 搜尋資料夾
        f_stmt = select(Folder).where(
            Folder.owner_id == owner_id,
            Folder.is_deleted == False,
            Folder.name.ilike(f"%{query}%")
        )
        f_res = await db.execute(f_stmt)
        folders = f_res.scalars().all()

        # 搜尋檔案
        file_stmt = select(File).where(
            File.owner_id == owner_id,
            File.is_deleted == False,
            File.name.ilike(f"%{query}%")
        )
        file_res = await db.execute(file_stmt)
        files = file_res.scalars().all()

        return {
            "folders": folders,
            "files": files
        }
