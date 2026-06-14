"""
虛擬檔案系統服務 (VFS Service)
職責：
1. 處理資料夾與檔案的 CRUD 核心業務邏輯
2. 實作導航核心 (UUID 查詢與麵包屑生成)
3. 確保所有操作皆符合擁有者權限驗證 (Security)
"""
import json
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.models import Folder, File, UploadSession
from app.schemas.vfs import Breadcrumb
from app import filesystem
from app.core.config import settings
from app.core.exceptions import (
    NodeNotFoundError,
    PermissionDeniedError,
    InvalidTicketError,
    TicketRateLimitError,
)

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
    async def prepare_download(db: AsyncSession, file_id: str, owner_id: str) -> File:
        """
        準備下載檔案：驗證檔案存在性、所有權與實體磁碟存在性。
        """
        # 1. 查詢檔案元數據
        stmt = select(File).where(File.id == file_id)
        result = await db.execute(stmt)
        file_obj = result.scalars().first()
        
        # 2. 驗證檔案是否存在與是否被刪除
        if not file_obj or file_obj.is_deleted:
            raise NodeNotFoundError("檔案不存在或無權限存取")
            
        # 3. 驗證檔案所有權
        if file_obj.owner_id != owner_id:
            raise PermissionDeniedError("權限不足，無法存取此檔案")
            
        # 4. 驗證實體磁碟檔案是否存在
        if not await filesystem.exists(file_obj.storage_path):
            raise NodeNotFoundError("下載失敗：實體檔案已遺失")
            
        return file_obj

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

    @staticmethod
    async def delete_node(db: AsyncSession, owner_id: str, node_id: str, node_type: str):
        """
        邏輯刪除節點。若是資料夾，則遞迴標記所有子項。
        """
        from datetime import datetime, timezone
        from app.core.exceptions import NodeNotFoundError, BaseBusinessException

        now = datetime.now(timezone.utc)

        if node_type == "folder":
            # 1. 驗證根資料夾是否存在
            root_folder = await VFSService.get_folder_by_id(db, node_id, owner_id)
            if not root_folder:
                raise NodeNotFoundError("資料夾不存在")

            # 禁止刪除根目錄
            if root_folder.parent_id is None:
                raise BaseBusinessException("禁止刪除根目錄", status_code=400)

            # 2. 獲取所有後代資料夾 ID (遞迴收集)
            all_folder_ids = [node_id]
            to_process = [node_id]
            
            # BFS add all
            while to_process:
                curr_id = to_process.pop()
                child_stmt = select(Folder.id).where(Folder.parent_id == curr_id, Folder.is_deleted == False)
                res = await db.execute(child_stmt)
                child_ids = res.scalars().all()
                all_folder_ids.extend(child_ids)
                to_process.extend(child_ids)

            # 3. 批量更新資料夾狀態
            await db.execute(
                update(Folder)
                .where(Folder.id.in_(all_folder_ids))
                .values(is_deleted=True, deleted_at=now)
            )

            # 4. 批量更新這些資料夾下的所有檔案
            await db.execute(
                update(File)
                .where(File.folder_id.in_(all_folder_ids))
                .values(is_deleted=True, deleted_at=now)
            )

        elif node_type == "file":
            # 單個檔案刪除
            node = await VFSService.get_file_by_id(db, node_id, owner_id)
            if not node:
                raise NodeNotFoundError("檔案不存在")
            
            node.is_deleted = True
            node.deleted_at = now
        else:
            raise BaseBusinessException("無效的節點類型", status_code=400)

        await db.commit()
        return {"message": "刪除成功", "deleted_nodes_count": "many" if node_type == "folder" else 1}

    @staticmethod
    async def init_upload(
        db: AsyncSession,
        filename: str,
        total_chunks: int,
        expected_hash: Optional[str],
        owner_id: str,
        target_folder_id: Optional[str] = None
    ) -> UploadSession:
        """
        初始化分塊上傳會話 (Step 4.3 第一階段)。
        """
        from app.core.exceptions import NodeNotFoundError

        # 1. 決定目標目錄並驗證權限
        if target_folder_id is None:
            root = await VFSService.get_or_create_root(db, owner_id)
            target_folder_id = root.id
        else:
            target_folder = await VFSService.get_folder_by_id(db, target_folder_id, owner_id)
            if not target_folder:
                raise NodeNotFoundError("目標資料夾不存在或無權限存取")

        # 2. 前置衝突防禦：檢查同名檔案 (File) 是否已存在且未刪除
        conflict_file_stmt = select(File).where(
            File.folder_id == target_folder_id,
            File.owner_id == owner_id,
            File.name == filename,
            File.is_deleted == False
        )
        conflict_file_res = await db.execute(conflict_file_stmt)
        if conflict_file_res.scalars().first():
            from app.core.exceptions import DuplicateNodeError
            raise DuplicateNodeError(f"目標目錄下已存在同名檔案 '{filename}'")

        # 3. 前置衝突防禦：檢查是否有針對該資料夾同名檔案的活躍上傳會話 (UploadSession)
        conflict_session_stmt = select(UploadSession).where(
            UploadSession.target_folder_id == target_folder_id,
            UploadSession.owner_id == owner_id,
            UploadSession.filename == filename
        )
        conflict_session_res = await db.execute(conflict_session_stmt)
        if conflict_session_res.scalars().first():
            from app.core.exceptions import BaseBusinessException
            raise BaseBusinessException(f"同名檔案 '{filename}' 的上傳會話已在進行中，請勿重複上傳", status_code=400)

        # 4. 建立上傳會話
        session = UploadSession(
            owner_id=owner_id,
            filename=filename,
            target_folder_id=target_folder_id,
            total_chunks=total_chunks,
            expected_hash=expected_hash
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def upload_chunk(
        db: AsyncSession,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
        owner_id: str
    ) -> None:
        """
        上傳單個分塊，包含 IDOR 擁有者校驗與索引校驗 (Step 4.3 第二階段)。
        """
        from app.core.exceptions import UploadSessionNotFoundError, UploadSessionValidationError

        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. IDOR 安全防禦：確保上傳者是會話擁有人
        if session.owner_id != owner_id:
            from app.core.exceptions import PermissionDeniedError
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 校驗分塊索引合法性
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            raise UploadSessionValidationError(f"無效的分塊索引：{chunk_index}，總分塊數為：{session.total_chunks}")

        # 4. 寫入實體暫存
        await filesystem.save_chunk(upload_id, chunk_index, chunk_data)

    @staticmethod
    async def finalize_upload(
        db: AsyncSession,
        upload_id: str,
        owner_id: str
    ) -> File:
        """
        物理合併暫存碎片、進行雜湊校驗、在資料庫完成虛擬「入籍」，最後清理暫存區 (Step 4.3 第三階段)。
        """
        from mimetypes import guess_type
        from app.core.exceptions import PermissionDeniedError, UploadSessionNotFoundError, UploadSessionValidationError

        # 1. 獲取會話並強校驗擁有者權限
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 2. 檢索現有已上傳的分塊索引列表
        uploaded_chunks = await filesystem.list_chunks(upload_id)
        missing_chunks = [i for i in range(session.total_chunks) if i not in uploaded_chunks]
        
        if missing_chunks:
            raise UploadSessionValidationError(f"分塊尚未上傳完畢，缺失分塊索引：{missing_chunks}")

        # 3. 流式物理合併所有碎片並計算大小與 SHA256 雜湊
        try:
            merged_info = await filesystem.merge_from_chunks(upload_id, session.total_chunks)
        except Exception as e:
            raise UploadSessionValidationError(f"實體合併失敗：{str(e)}")

        # 4. 校驗雜湊完整性 (比對前端預期與實體合併計算的 Hash)
        if session.expected_hash:
            calculated_hash = merged_info["hash"]
            if calculated_hash.lower() != session.expected_hash.lower():
                # 雜湊不符，代表檔案傳輸損毀，物理刪除剛合併的正式檔案並拋出異常
                await filesystem.delete_file(merged_info["storage_name"])
                raise UploadSessionValidationError("檔案雜湊校驗失敗 (Hash mismatch)，檔案可能在傳輸中損毀。")

        # 5. 檔案「正式入籍」虛擬檔案系統 (VFS)
        # 決定目標虛擬資料夾，若無則歸屬於使用者的 Root
        target_folder_id = session.target_folder_id
        if not target_folder_id:
            root = await VFSService.get_or_create_root(db, owner_id)
            target_folder_id = root.id

        # 檢查目標目錄下的命名衝突
        conflict_stmt = select(File).where(
            File.folder_id == target_folder_id,
            File.owner_id == owner_id,
            File.name == session.filename,
            File.is_deleted == False
        )
        conflict_res = await db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            # 有同名檔案，物理刪除剛合併的正式檔案並拋出異常
            await filesystem.delete_file(merged_info["storage_name"])
            from app.core.exceptions import DuplicateNodeError
            raise DuplicateNodeError(f"目標目錄下已存在名為 '{session.filename}' 的檔案")

        # 推測檔案 MIME 類型
        mime_type, _ = guess_type(session.filename)

        new_file = File(
            name=session.filename,
            folder_id=target_folder_id,
            owner_id=owner_id,
            size=merged_info["size"],
            mime_type=mime_type,
            storage_path=merged_info["storage_name"],
            hash_sha256=merged_info["hash"]
        )
        db.add(new_file)

        # 6. 物理清理暫存碎塊會話與碎片
        await db.delete(session)
        await db.commit()
        await db.refresh(new_file)

        # 清除暫存目錄碎片
        await filesystem.cleanup_temp(upload_id)

        return new_file

    @staticmethod
    async def get_upload_status(
        db: AsyncSession,
        upload_id: str,
        owner_id: str
    ) -> dict:
        """
        獲取分塊上傳會話的進度狀態與缺失分塊。
        """
        from app.core.exceptions import UploadSessionNotFoundError

        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. 安全防禦：確保查詢者是會話擁有人
        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 讀取實體已存在的分塊列表 (呼叫原子操作 list_chunks)
        uploaded_chunks = await filesystem.list_chunks(upload_id)
        uploaded_chunks.sort()

        # 4. 計算缺失分塊 (差集)
        all_chunks_set = set(range(session.total_chunks))
        uploaded_chunks_set = set(uploaded_chunks)
        missing_chunks = list(all_chunks_set - uploaded_chunks_set)
        missing_chunks.sort()

        return {
            "upload_id": session.id,
            "filename": session.filename,
            "total_chunks": session.total_chunks,
            "uploaded_chunks": uploaded_chunks,
            "missing_chunks": missing_chunks
        }

    @staticmethod
    async def cancel_upload(
        db: AsyncSession,
        upload_id: str,
        owner_id: str
    ) -> dict:
        """
        主動取消上傳會話，清除資料庫紀錄並物理刪除磁碟暫存分塊目錄。
        """
        from app.core.exceptions import UploadSessionNotFoundError

        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. 安全防禦：確保取消者是會話擁有人 (IDOR 防禦)
        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 刪除資料庫會話記錄
        await db.delete(session)
        await db.commit()

        # 4. 物理物理原子操作清理磁碟暫存分塊
        await filesystem.cleanup_temp(upload_id)

        return {
            "message": "上傳會話與磁碟暫存已成功取消並物理清除",
            "upload_id": upload_id
        }

    @staticmethod
    async def create_download_ticket(
        db: AsyncSession,
        redis_client,
        file_id: str,
        owner_id: str
    ) -> str:
        """
        驗證使用者的下載權限，並生成或複用一個臨時下載 Ticket UUID。
        在指定的 TTL 時間內對同一使用者與同一檔案重複申請，直接複用已存在的 UUID，不生成新憑證。
        """
        # 1. 驗證檔案存在性與擁有者權限
        await VFSService.prepare_download(db=db, file_id=file_id, owner_id=owner_id)

        # 2. 查詢防刷鎖，指定時間內存在則直接複用
        user_download_key = f"vfs:ticket:user_download:{owner_id}:{file_id}"
        existing_ticket = await redis_client.get(user_download_key)
        if existing_ticket:
            return existing_ticket

        # 3. 生成新的 Ticket UUID 與憑證資料
        ticket_uuid = str(uuid.uuid4())
        ticket_data = json.dumps({"file_id": file_id, "owner_id": owner_id})
        ticket_key = f"vfs:ticket:download:{ticket_uuid}"

        # 4. 寫入 Redis 雙向映射，到期自然過期消亡
        await redis_client.set(user_download_key, ticket_uuid, ex=settings.DOWNLOAD_TICKET_TTL)
        await redis_client.set(ticket_key, ticket_data, ex=settings.DOWNLOAD_TICKET_TTL)

        return ticket_uuid

    @staticmethod
    async def verify_and_prepare_download(
        db: AsyncSession,
        redis_client,
        file_id: str,
        ticket: str
    ) -> File:
        """
        從 Redis 驗證 Ticket 憑證的有效性與連線數上限，通過後返回實體檔案物件。
        連線計數只增不減，完全依靠 TTL 自動清理，不在 finally 中執行 Redis 操作。
        """
        ticket_key = f"vfs:ticket:download:{ticket}"
        active_conns_key = f"vfs:ticket:active_conns:{ticket}"

        # 1. 驗證憑證存在且未過期
        ticket_data_raw = await redis_client.get(ticket_key)
        if not ticket_data_raw:
            raise InvalidTicketError("無效或已過期的下載憑證")

        # 2. 解析憑證內容
        try:
            ticket_data = json.loads(ticket_data_raw)
        except Exception:
            raise InvalidTicketError("憑證資料解析錯誤")

        # 3. 確認憑證指派的檔案與請求一致
        if ticket_data.get("file_id") != file_id:
            raise InvalidTicketError("下載憑證與檔案不符")

        owner_id = ticket_data.get("owner_id")

        # 4. 原子累加連線計數，首次連線時設定 TTL
        new_conn_count = await redis_client.incr(active_conns_key)
        if new_conn_count == 1:
            await redis_client.expire(active_conns_key, settings.DOWNLOAD_TICKET_TTL)

        # 5. 超過上限直接阻斷，不手動刪除或遞減，固定等 TTL 自動消亡
        if new_conn_count > settings.DOWNLOAD_TICKET_MAX_REQUESTS:
            raise TicketRateLimitError("該憑證的下載請求次數已達上限")

        # 6. 通過所有驗證後，呼叫既有業務邏輯校驗檔案狀態與磁碟完整性
        return await VFSService.prepare_download(
            db=db,
            file_id=file_id,
            owner_id=owner_id
        )
