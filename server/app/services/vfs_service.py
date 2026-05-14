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
    async def create_folder(db: AsyncSession, owner_id: str, name: str, parent_id: Optional[str] = None) -> Folder:
        """
        建立一個虛擬資料夾節點 (純虛擬變更)。
        """
        # 1. 決定父目錄：若未提供，則設為 Root
        if parent_id is None:
            root = await VFSService.get_or_create_root(db, owner_id)
            parent_id = root.id
        else:
            # 驗證父目錄是否存在且屬於該使用者
            parent = await VFSService.get_folder_by_id(db, parent_id, owner_id)
            if not parent:
                from app.core.exceptions import NodeNotFoundError
                raise NodeNotFoundError("父目錄不存在")

        # 2. 檢查同級命名衝突 (排除已邏輯刪除的資料夾)
        conflict_stmt = select(Folder).where(
            Folder.parent_id == parent_id,
            Folder.owner_id == owner_id,
            Folder.name == name,
            Folder.is_deleted == False
        )
        conflict_res = await db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            from app.core.exceptions import DuplicateNodeError
            raise DuplicateNodeError(f"目錄已存在名為 '{name}' 的資料夾")

        # 3. 建立並儲存
        new_folder = Folder(
            name=name,
            parent_id=parent_id,
            owner_id=owner_id
        )
        db.add(new_folder)
        await db.commit()
        await db.refresh(new_folder)

        return new_folder

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

    @staticmethod
    async def rename_node(db: AsyncSession, owner_id: str, node_id: str, node_type: str, new_name: str):
        """
        重新命名虛擬節點 (檔案或資料夾)。
        """
        from app.core.exceptions import NodeNotFoundError, DuplicateNodeError

        # 1. 獲取目標節點並驗證權限
        if node_type == "folder":
            node = await VFSService.get_folder_by_id(db, node_id, owner_id)
            if not node:
                raise NodeNotFoundError("資料夾不存在")
            
            # 檢查同目錄下的命名衝突
            conflict_stmt = select(Folder).where(
                Folder.parent_id == node.parent_id,
                Folder.owner_id == owner_id,
                Folder.name == new_name,
                Folder.is_deleted == False,
                Folder.id != node_id
            )
        elif node_type == "file":
            node = await VFSService.get_file_by_id(db, node_id, owner_id)
            if not node:
                raise NodeNotFoundError("檔案不存在")
            
            # 檢查同目錄下的命名衝突
            conflict_stmt = select(File).where(
                File.folder_id == node.folder_id,
                File.owner_id == owner_id,
                File.name == new_name,
                File.is_deleted == False,
                File.id != node_id
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無效的節點類型")

        # 2. 執行衝突檢查
        conflict_res = await db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            raise DuplicateNodeError(f"該目錄下已存在名為 '{new_name}' 的物件")

        # 3. 更新名稱
        node.name = new_name
        await db.commit()
        await db.refresh(node)
        
        return node

    @staticmethod
    async def move_node(db: AsyncSession, owner_id: str, node_id: str, node_type: str, target_parent_id: Optional[str] = None):
        """
        搬移虛擬節點 (檔案或資料夾) 到新的目錄。
        包含：防循環檢查、衝突檢查、權限驗證。
        """
        from app.core.exceptions import NodeNotFoundError, DuplicateNodeError, BaseBusinessException

        # 1. 獲取目標父目錄
        if target_parent_id is None:
            root = await VFSService.get_or_create_root(db, owner_id)
            target_parent_id = root.id
        
        target_folder = await VFSService.get_folder_by_id(db, target_parent_id, owner_id)
        if not target_folder:
            raise NodeNotFoundError("目標目錄不存在")

        # 2. 獲取要搬移的節點
        if node_type == "folder":
            node = await VFSService.get_folder_by_id(db, node_id, owner_id)
            if not node:
                raise NodeNotFoundError("資料夾不存在")
            
            # --- [大專案邏輯：防循環檢查] ---
            # 不能將自己移入自己
            if node.id == target_parent_id:
                raise BaseBusinessException("不能將資料夾移入自身", status_code=400)
            
            # 溯源檢查：從目標父目錄一路往上爬，看會不會遇到自己
            curr_trace_id = target_folder.parent_id
            while curr_trace_id:
                if curr_trace_id == node.id:
                    raise BaseBusinessException("不能將資料夾移入其子目錄 (發生循環引用)", status_code=400)
                
                # 繼續往上找
                trace_node = await VFSService.get_folder_by_id(db, curr_trace_id, owner_id)
                if not trace_node: break
                curr_trace_id = trace_node.parent_id
            
            # 檢查目標目錄下的命名衝突
            conflict_stmt = select(Folder).where(
                Folder.parent_id == target_parent_id,
                Folder.owner_id == owner_id,
                Folder.name == node.name,
                Folder.is_deleted == False,
                Folder.id != node_id
            )
        elif node_type == "file":
            node = await VFSService.get_file_by_id(db, node_id, owner_id)
            if not node:
                raise NodeNotFoundError("檔案不存在")
            
            # 檢查目標目錄下的命名衝突
            conflict_stmt = select(File).where(
                File.folder_id == target_parent_id,
                File.owner_id == owner_id,
                File.name == node.name,
                File.is_deleted == False,
                File.id != node_id
            )
        else:
            raise BaseBusinessException("無效的節點類型", status_code=400)

        # 3. 執行衝突檢查
        conflict_res = await db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            raise DuplicateNodeError(f"目標目錄下已存在名為 '{node.name}' 的物件")

        # 4. 執行搬移
        if node_type == "folder":
            node.parent_id = target_parent_id
        else:
            node.folder_id = target_parent_id
            
        await db.commit()
        await db.refresh(node)
        
        return node
