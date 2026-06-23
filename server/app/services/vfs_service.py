"""
虛擬檔案系統服務 (VFS Service)
職責：
1. 處理資料夾與檔案的 CRUD 核心業務邏輯
2. 實作導航核心 (UUID 查詢與麵包屑生成)
3. 確保所有操作皆符合擁有者權限驗證 (Security)
"""
import json
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from mimetypes import guess_type
from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models import Folder, File, UploadSession
from app.schemas.vfs import Breadcrumb, BrowseResponse
from app.filesystem.base import BaseStorage
from app.core.config import settings
from app.core.exceptions import (
    NodeNotFoundError,
    PermissionDeniedError,
    InvalidTicketError,
    TicketRateLimitError,
    BaseBusinessException,
    DuplicateNodeError,
    UploadSessionNotFoundError,
    UploadSessionValidationError,
)


class VFSService:
    """
    虛擬檔案系統服務 (VFS Service)
    職責：處理檔案與目錄的 CRUD 業務邏輯，並確保資料安全與一致性。
    """
    def __init__(self, db: AsyncSession, storage: BaseStorage, redis_client: Redis):
        self.db = db
        self.storage = storage
        self.redis_client = redis_client

    async def get_folder_by_id(self, folder_id: str, owner_id: str) -> Optional[Folder]:
        """
        根據 UUID 獲取資料夾，並驗證擁有者與刪除狀態。
        """
        stmt = select(Folder).where(
            Folder.id == folder_id,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_file_by_id(self, file_id: str, owner_id: str) -> Optional[File]:
        """
        根據 UUID 獲取檔案，並驗證擁有者與刪除狀態。
        """
        stmt = select(File).where(
            File.id == file_id,
            File.owner_id == owner_id,
            File.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def prepare_download(self, file_id: str, owner_id: str) -> File:
        """
        準備下載檔案：驗證檔案存在性、所有權與實體磁碟存在性。
        """
        # 1. 查詢檔案元數據
        stmt = select(File).where(File.id == file_id)
        result = await self.db.execute(stmt)
        file_obj = result.scalars().first()
        
        # 2. 驗證檔案是否存在與是否被刪除
        if not file_obj or file_obj.is_deleted:
            raise NodeNotFoundError("檔案不存在或無權限存取")
            
        # 3. 驗證檔案所有權
        if file_obj.owner_id != owner_id:
            raise PermissionDeniedError("權限不足，無法存取此檔案")
            
        # 4. 驗證實體磁碟檔案是否存在
        if not await self.storage.exists(file_obj.storage_path):
            raise NodeNotFoundError("下載失敗：實體檔案已遺失")
            
        return file_obj

    async def get_breadcrumbs(self, folder_id: Optional[str], owner_id: str) -> List[Breadcrumb]:
        """
        生成從根目錄到指定目錄的麵包屑路徑。
        """
        breadcrumbs = []
        current_id = folder_id

        while current_id:
            folder = await self.get_folder_by_id(current_id, owner_id)
            if folder is None:
                break
            
            # 插入到清單最前面 (因為我們是從下往上找)
            breadcrumbs.insert(0, Breadcrumb(id=folder.id, name=folder.name))
            
            # 往上一層
            current_id = folder.parent_id

        return breadcrumbs
    async def get_or_create_root(self, owner_id: str) -> Folder:
        """
        獲取使用者的根目錄，如果不存在則自動建立一個。
        """
        # 1. 查詢 Root (parent_id 為 None 的資料夾)
        stmt = select(Folder).where(
            Folder.parent_id == None,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        )
        result = await self.db.execute(stmt)
        root = result.scalars().first()

        # 2. 如果不存在，則建立
        if root is None:
            root = Folder(
                name = "Root",
                parent_id = None,
                owner_id = owner_id
            )
            self.db.add(root)
            await self.db.commit()
            await self.db.refresh(root) 
            # 有些資料是 commit 後算的，所以需要 refresh 更新 root
        
        return root

    async def get_browse_data(self, folder_id: Optional[str], owner_id: str) -> Dict[str, Any]:
        """
        獲取目錄瀏覽資料 (包含當前資料夾、子資料夾、子檔案與麵包屑，自帶 Redis 快取優化)。
        """
        use_cache = bool(settings.VFS_DIRECTORY_CACHE_ENABLED and self.redis_client)

        # 1. 決定 target_id (如果 folder_id 是 None 則獲取/建立 Root)
        target_id = folder_id
        if folder_id is None:
            root_cached_key = f"vfs:cache:root_folder_id:{owner_id}"
            cached_root_id = None
            if use_cache:
                try:
                    cached_root_id = await self.redis_client.get(root_cached_key)
                except Exception as e:
                    print(f"[VFS Cache Error] Failed to get root cached ID: {e}")
                    use_cache = False  # 發生異常時，本次執行關閉快取

            if use_cache and cached_root_id:
                target_id = cached_root_id
            else:
                root = await self.get_or_create_root(owner_id)
                target_id = root.id
                if use_cache:
                    try:
                        await self.redis_client.set(root_cached_key, target_id)
                    except Exception as e:
                        print(f"[VFS Cache Error] Failed to set root cached ID: {e}")
                        use_cache = False
        else:
            target_id = folder_id

        # 2. 嘗試讀取目錄瀏覽快取
        cache_key = f"vfs:cache:browse:{owner_id}:{target_id}"
        if use_cache:
            try:
                cached_json = await self.redis_client.get(cache_key)
                if cached_json:
                    return json.loads(cached_json)
            except Exception as e:
                print(f"[VFS Cache Error] Failed to read browse cache: {e}")
                use_cache = False

        # 3. 快取未命中：讀取資料庫
        current_folder = await self.get_folder_by_id(target_id, owner_id)
        if not current_folder:
            # 如果是獲取 Root 資料夾但資料庫中不存在（可能資料庫重建或被刪除），則清理無效快取並重新建立
            if folder_id is None:
                if use_cache:
                    try:
                        root_cached_key = f"vfs:cache:root_folder_id:{owner_id}"
                        await self.redis_client.delete(root_cached_key)
                    except Exception as e:
                        print(f"[VFS Cache Error] Failed to delete invalid root cache: {e}")
                        use_cache = False
                root = await self.get_or_create_root(owner_id)
                target_id = root.id
                if use_cache:
                    try:
                        await self.redis_client.set(root_cached_key, target_id)
                    except Exception as e:
                        print(f"[VFS Cache Error] Failed to reset root cached ID: {e}")
                        use_cache = False
                current_folder = await self.get_folder_by_id(target_id, owner_id)
                if not current_folder:
                    raise NodeNotFoundError("資料夾不存在或無權限存取")
            else:
                raise NodeNotFoundError("資料夾不存在或無權限存取")

        # 獲取子資料夾
        folder_stmt = select(Folder).where(
            Folder.parent_id == target_id,
            Folder.owner_id == owner_id,
            Folder.is_deleted == False
        ).order_by(Folder.name.asc())
        folders_res = await self.db.execute(folder_stmt)
        folders = folders_res.scalars().all()

        # 獲取子檔案
        file_stmt = select(File).where(
            File.folder_id == target_id,
            File.owner_id == owner_id,
            File.is_deleted == False
        ).order_by(File.name.asc())
        files_res = await self.db.execute(file_stmt)
        files = files_res.scalars().all()

        # 獲取麵包屑
        breadcrumbs = await self.get_breadcrumbs(target_id, owner_id)

        # 4. 序列化與快取寫入 (格式對齊 schemas.vfs.BrowseResponse)
        response_model = BrowseResponse(
            current_folder=current_folder,
            breadcrumbs=breadcrumbs,
            subfolders=folders,
            files=files
        )

        response_dict = json.loads(response_model.model_dump_json())

        if use_cache:
            try:
                await self.redis_client.set(
                    cache_key,
                    response_model.model_dump_json(),
                    ex=settings.VFS_DIRECTORY_CACHE_TTL
                )
            except Exception as e:
                print(f"[VFS Cache Error] Failed to write browse cache: {e}")

        return response_dict


    async def _clear_browse_cache(self, owner_id: str, folder_id: Optional[str] = None):
        """
        清理目錄瀏覽快取 (延遲雙刪除機制)。
        使用 asyncio.create_task 進行非同步背景執行，以防阻塞主 API。
        """
        if not settings.VFS_DIRECTORY_CACHE_ENABLED or self.redis_client is None:
            return


        async def delete_task():
            key = f"vfs:cache:browse:{owner_id}:{folder_id}" if folder_id else None
            pattern = f"vfs:cache:browse:{owner_id}:*"
            # 第一刪：即時刪除
            if folder_id:
                await self.redis_client.delete(key)
            else:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break

            # 第二刪：延遲 1.0 秒刪除，排除讀寫併發髒數據
            await asyncio.sleep(1.0)
            if folder_id:
                await self.redis_client.delete(key)
            else:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break

        # 註冊至背景執行
        asyncio.create_task(delete_task())

    async def create_folder(self, owner_id: str, name: str, parent_id: Optional[str] = None) -> Folder:
        """
        建立一個虛擬資料夾節點 (純虛擬變更)。
        """
        # 1. 決定父目錄：若未提供，則設為 Root
        if parent_id is None:
            root = await self.get_or_create_root(owner_id)
            parent_id = root.id
        else:
            # 驗證父目錄是否存在且屬於該使用者
            parent = await self.get_folder_by_id(parent_id, owner_id)
            if not parent:
                raise NodeNotFoundError("父目錄不存在")

        # 2. 檢查同級命名衝突 (排除已邏輯刪除的資料夾)
        conflict_stmt = select(Folder).where(
            Folder.parent_id == parent_id,
            Folder.owner_id == owner_id,
            Folder.name == name,
            Folder.is_deleted == False
        )
        conflict_res = await self.db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            raise DuplicateNodeError(f"目錄已存在名為 '{name}' 的資料夾")

        # 3. 建立並儲存
        new_folder = Folder(
            name=name,
            parent_id=parent_id,
            owner_id=owner_id
        )
        self.db.add(new_folder)
        await self.db.commit()
        await self.db.refresh(new_folder)

        # 4. 快取失效 (即時與非同步延遲刪除父目錄快取)
        await self._clear_browse_cache(owner_id, parent_id)

        return new_folder


    async def search_nodes(self, owner_id: str, query: str):
        """
        模糊搜尋使用者擁有的所有資料夾與檔案。
        """
        # 搜尋資料夾
        f_stmt = select(Folder).where(
            Folder.owner_id == owner_id,
            Folder.is_deleted == False,
            Folder.name.ilike(f"%{query}%")
        )
        f_res = await self.db.execute(f_stmt)
        folders = f_res.scalars().all()

        # 搜尋檔案
        file_stmt = select(File).where(
            File.owner_id == owner_id,
            File.is_deleted == False,
            File.name.ilike(f"%{query}%")
        )
        file_res = await self.db.execute(file_stmt)
        files = file_res.scalars().all()

        return {
            "folders": folders,
            "files": files
        }

    async def rename_node(self, owner_id: str, node_id: str, node_type: str, new_name: str):
        """
        重新命名虛擬節點 (檔案或資料夾)。
        """
        # 1. 獲取目標節點並驗證權限
        if node_type == "folder":
            node = await self.get_folder_by_id(node_id, owner_id)
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
            node = await self.get_file_by_id(node_id, owner_id)
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
            raise BaseBusinessException("無效的節點類型", status_code=400)

        # 2. 執行衝突檢查
        conflict_res = await self.db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            raise DuplicateNodeError(f"該目錄下已存在名為 '{new_name}' 的物件")

        # 3. 更新名稱
        node.name = new_name
        await self.db.commit()
        await self.db.refresh(node)

        # 4. 快取失效
        if node_type == "folder":
            await self._clear_browse_cache(owner_id, node.parent_id)
            await self._clear_browse_cache(owner_id, node.id)
        else:
            await self._clear_browse_cache(owner_id, node.folder_id)
        
        return node

    async def move_node(self, owner_id: str, node_id: str, node_type: str, target_parent_id: Optional[str] = None):
        """
        搬移虛擬節點 (檔案或資料夾) 到新的目錄。
        包含：防循環檢查、衝突檢查、權限驗證。
        """
        # 1. 獲取目標父目錄
        if target_parent_id is None:
            root = await self.get_or_create_root(owner_id)
            target_parent_id = root.id
        
        target_folder = await self.get_folder_by_id(target_parent_id, owner_id)
        if not target_folder:
            raise NodeNotFoundError("目標目錄不存在")

        # 2. 獲取要搬移的節點
        if node_type == "folder":
            node = await self.get_folder_by_id(node_id, owner_id)
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
                trace_node = await self.get_folder_by_id(curr_trace_id, owner_id)
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
            node = await self.get_file_by_id(node_id, owner_id)
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
        conflict_res = await self.db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            raise DuplicateNodeError(f"目標目錄下已存在名為 '{node.name}' 的物件")

        # 4. 執行搬移
        if node_type == "folder":
            node.parent_id = target_parent_id
        else:
            node.folder_id = target_parent_id
            
        await self.db.commit()
        await self.db.refresh(node)

        # 5. 快取失效 (搬移直接全目錄失效以防子孫目錄麵包屑不一致)
        await self._clear_browse_cache(owner_id, None)
        
        return node

    async def delete_node(self, owner_id: str, node_id: str, node_type: str):
        """
        邏輯刪除節點。若是資料夾，則遞迴標記所有子項。
        """
        now = datetime.now(timezone.utc)

        if node_type == "folder":
            # 1. 驗證根資料夾是否存在
            root_folder = await self.get_folder_by_id(node_id, owner_id)
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
                res = await self.db.execute(child_stmt)
                child_ids = res.scalars().all()
                all_folder_ids.extend(child_ids)
                to_process.extend(child_ids)

            # 3. 批量更新資料夾狀態
            await self.db.execute(
                update(Folder)
                .where(Folder.id.in_(all_folder_ids))
                .values(is_deleted=True, deleted_at=now)
            )

            # 4. 批量更新這些資料夾下的所有檔案
            await self.db.execute(
                update(File)
                .where(File.folder_id.in_(all_folder_ids))
                .values(is_deleted=True, deleted_at=now)
            )

        elif node_type == "file":
            # 單個檔案刪除
            node = await self.get_file_by_id(node_id, owner_id)
            if not node:
                raise NodeNotFoundError("檔案不存在")
            
            parent_folder_id = node.folder_id
            node.is_deleted = True
            node.deleted_at = now
        else:
            raise BaseBusinessException("無效的節點類型", status_code=400)

        await self.db.commit()

        # 5. 快取失效
        if node_type == "folder":
            await self._clear_browse_cache(owner_id, None)
        else:
            await self._clear_browse_cache(owner_id, parent_folder_id)

        return {"message": "刪除成功", "deleted_nodes_count": "many" if node_type == "folder" else 1}

    async def init_upload(
        self,
        filename: str,
        total_size: int,
        chunk_size: int,
        last_modified: int,
        owner_id: str,
        target_folder_id: Optional[str] = None
    ) -> UploadSession:
        """
        初始化分塊上傳會話 (Step 4.3 第一階段)。
        """
        # 1. 決定目標目錄並驗證權限
        if target_folder_id is None:
            root = await self.get_or_create_root(owner_id)
            target_folder_id = root.id
        else:
            target_folder = await self.get_folder_by_id(target_folder_id, owner_id)
            if not target_folder:
                raise NodeNotFoundError("目標資料夾不存在或無權限存取")

        # 2. 前置衝突防禦：檢查同名檔案 (File) 是否已存在且未刪除
        conflict_file_stmt = select(File).where(
            File.folder_id == target_folder_id,
            File.owner_id == owner_id,
            File.name == filename,
            File.is_deleted == False
        )
        conflict_file_res = await self.db.execute(conflict_file_stmt)
        if conflict_file_res.scalars().first():
            raise DuplicateNodeError(f"目標目錄下已存在同名檔案 '{filename}'")

        # 3. 前置衝突防禦：檢查是否有針對該資料夾同名檔案的活躍上傳會話 (UploadSession)
        conflict_session_stmt = select(UploadSession).where(
            UploadSession.target_folder_id == target_folder_id,
            UploadSession.owner_id == owner_id,
            UploadSession.filename == filename
        )
        conflict_session_res = await self.db.execute(conflict_session_stmt)
        conflict_session = conflict_session_res.scalars().first()

        if conflict_session:
            if conflict_session.last_modified != last_modified:
                # 檔案特徵 (last_modified) 已改變，證明舊有會話已是無效幽靈
                # 主動將其銷毀以解除死鎖，放行本次全新上傳
                await self.cancel_upload(conflict_session.id, owner_id)
            else:
                # 檔案特徵一模一樣，可能正在別的分頁積極上傳中，嚴格拒絕以保護該上傳
                raise BaseBusinessException(f"同名檔案 '{filename}' 的上傳會話已在進行中，請勿重複上傳", status_code=400)

        # 4. 計算分塊數並建立上傳會話
        total_chunks = (total_size + chunk_size - 1) // chunk_size if chunk_size > 0 else 0
        
        session = UploadSession(
            owner_id=owner_id,
            filename=filename,
            target_folder_id=target_folder_id,
            total_chunks=total_chunks,
            total_size=total_size,
            chunk_size=chunk_size,
            last_modified=last_modified
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        # 5. 預分配 Sparse File 實體空間
        await self.storage.init_sparse_file(session.id, total_size)
        
        return session

    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_data: bytes,
        owner_id: str
    ) -> None:
        """
        上傳單個分塊，包含 IDOR 擁有者校驗與索引校驗 (Step 4.3 第二階段)。
        """
        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. IDOR 安全防禦：確保上傳者是會話擁有人
        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 校驗分塊索引合法性
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            raise UploadSessionValidationError(f"無效的分塊索引：{chunk_index}，總分塊數為：{session.total_chunks}")

        # 4. 寫入實體暫存 (隨機寫入)
        offset = chunk_index * session.chunk_size
        await self.storage.save_chunk(upload_id, offset, chunk_data)

        # 5. 將已上傳的分塊寫入 Redis 追蹤進度，設定 24H 過期
        progress_key = f"vfs:upload_progress:{upload_id}"
        await self.redis_client.sadd(progress_key, chunk_index)
        await self.redis_client.expire(progress_key, 86400)

    async def finalize_upload(
        self,
        upload_id: str,
        owner_id: str
    ) -> File:
        """
        物理合併暫存碎片、進行雜湊校驗、在資料庫完成虛擬「入籍」，最後清理暫存區 (Step 4.3 第三階段)。
        """
        # 1. 獲取會話並強校驗擁有者權限
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 2. 檢索現有已上傳的分塊索引列表 (自 Redis)
        progress_key = f"vfs:upload_progress:{upload_id}"
        uploaded_chunks_str = await self.redis_client.smembers(progress_key)
        uploaded_chunks = [int(x) for x in uploaded_chunks_str]
        missing_chunks = [i for i in range(session.total_chunks) if i not in uploaded_chunks]
        
        if missing_chunks:
            raise UploadSessionValidationError(f"分塊尚未上傳完畢，缺失分塊索引：{missing_chunks}")

        # 3. 物理驗證與正式入籍
        try:
            merged_info = await self.storage.finalize_file(upload_id)
        except Exception as e:
            raise UploadSessionValidationError(f"實體校驗入籍失敗：{str(e)}")

        # 4. 檔案「正式入籍」虛擬檔案系統 (VFS)
        # 決定目標虛擬資料夾，若無則歸屬於使用者的 Root
        target_folder_id = session.target_folder_id
        if not target_folder_id:
            root = await self.get_or_create_root(owner_id)
            target_folder_id = root.id

        # 檢查目標目錄下的命名衝突
        conflict_stmt = select(File).where(
            File.folder_id == target_folder_id,
            File.owner_id == owner_id,
            File.name == session.filename,
            File.is_deleted == False
        )
        conflict_res = await self.db.execute(conflict_stmt)
        if conflict_res.scalars().first():
            # 有同名檔案，物理刪除剛合併的正式檔案並拋出異常
            await self.storage.delete_file(merged_info["storage_name"])
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
        self.db.add(new_file)

        # 6. 物理清理暫存碎塊會話與碎片
        await self.db.delete(session)
        await self.db.commit()
        await self.db.refresh(new_file)

        # 清除暫存目錄碎片與 Redis 進度追蹤
        await self.storage.cleanup_temp(upload_id)
        await self.redis_client.delete(progress_key)

        # 7. 清理快取
        await self._clear_browse_cache(owner_id, new_file.folder_id)

        return new_file

    async def resume_upload(
        self,
        upload_id: str,
        owner_id: str,
        target_folder_id: Optional[str],
        last_modified: int
    ) -> Dict[str, Any]:
        """
        發起斷點續傳會話，進行特徵防呆驗證與目標資料夾重定向，並回傳進度狀態與缺失分塊。
        """

        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. 安全防禦：確保查詢者是會話擁有人
        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 特徵防禦校驗：比對最後修改時間
        if session.last_modified != last_modified:
            # 檔案已被修改，舊有的分塊與會話已無效
            # 必須主動銷毀舊會話，否則前端退回 init_upload 時會遇到「同名檔案已在上傳中」的死鎖
            await self.cancel_upload(upload_id, owner_id)
            raise UploadSessionValidationError("檔案特徵 (last_modified) 已變更，無法續傳，請重新發起全新上傳。")

        # 4. 目標資料夾重定向檢查
        if target_folder_id is not None and session.target_folder_id != target_folder_id:
            # 驗證目標資料夾權限
            target_folder = await self.get_folder_by_id(target_folder_id, owner_id)
            if not target_folder:
                raise NodeNotFoundError("目標資料夾不存在或無權限存取")
                
            # 檢查目標目錄下的命名衝突 (正式檔案)
            conflict_file_stmt = select(File).where(
                File.folder_id == target_folder_id,
                File.owner_id == owner_id,
                File.name == session.filename,
                File.is_deleted == False
            )
            conflict_file_res = await self.db.execute(conflict_file_stmt)
            if conflict_file_res.scalars().first():
                raise DuplicateNodeError(f"目標目錄下已存在名為 '{session.filename}' 的檔案")
                
            # 檢查活躍會話衝突
            conflict_session_stmt = select(UploadSession).where(
                UploadSession.target_folder_id == target_folder_id,
                UploadSession.owner_id == owner_id,
                UploadSession.filename == session.filename,
                UploadSession.id != upload_id
            )
            conflict_session_res = await self.db.execute(conflict_session_stmt)
            if conflict_session_res.scalars().first():
                raise DuplicateNodeError(f"目標目錄下已有同名檔案 '{session.filename}' 正在上傳中")
                
            # 變更目標資料夾
            session.target_folder_id = target_folder_id
            await self.db.commit()

        # 5. 從 Redis 讀取實體已存在的分塊列表
        progress_key = f"vfs:upload_progress:{upload_id}"
        uploaded_chunks_str = await self.redis_client.smembers(progress_key)
        uploaded_chunks = [int(x) for x in uploaded_chunks_str]
        uploaded_chunks.sort()

        # 6. 計算缺失分塊 (差集)
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

    async def cancel_upload(
        self,
        upload_id: str,
        owner_id: str
    ) -> Dict[str, Any]:
        """
        主動取消上傳會話，清除資料庫紀錄並物理刪除磁碟暫存分塊目錄。
        """

        # 1. 查詢上傳會話
        stmt = select(UploadSession).where(UploadSession.id == upload_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()

        if not session:
            raise UploadSessionNotFoundError()

        # 2. 安全防禦：確保取消者是會話擁有人 (IDOR 防禦)
        if session.owner_id != owner_id:
            raise PermissionDeniedError("無權存取此上傳會話")

        # 3. 刪除資料庫會話記錄
        await self.db.delete(session)
        await self.db.commit()

        # 4. 物理清理磁碟暫存分塊檔案，並清除 Redis 進度
        await self.storage.cleanup_temp(upload_id)
        await self.redis_client.delete(f"vfs:upload_progress:{upload_id}")

        return {
            "message": "上傳會話與磁碟暫存已成功取消並物理清除",
            "upload_id": upload_id
        }

    async def create_download_ticket(
        self,
        file_id: str,
        owner_id: str
    ) -> str:
        """
        驗證使用者的下載權限，並生成或複用一個臨時下載 Ticket UUID。
        在指定的 TTL 時間內對同一使用者與同一檔案重複申請，直接複用已存在的 UUID，不生成新憑證。
        """
        # 1. 驗證檔案存在性與擁有者權限
        await self.prepare_download(file_id=file_id, owner_id=owner_id)

        # 2. 查詢防刷鎖，指定時間內存在則直接複用
        user_download_key = f"vfs:ticket:user_download:{owner_id}:{file_id}"
        existing_ticket = await self.redis_client.get(user_download_key)
        if existing_ticket:
            # 防範雙向映射過期時間差或內存驅逐不一致，確認憑證主體確實存在
            if await self.redis_client.exists(f"vfs:ticket:download:{existing_ticket}"):
                return existing_ticket

        # 3. 生成新的 Ticket UUID 與憑證資料
        ticket_uuid = str(uuid.uuid4())
        ticket_data = json.dumps({"file_id": file_id, "owner_id": owner_id})
        ticket_key = f"vfs:ticket:download:{ticket_uuid}"

        # 4. 寫入 Redis 雙向映射，到期自然過期消亡
        await self.redis_client.set(user_download_key, ticket_uuid, ex=settings.DOWNLOAD_TICKET_TTL)
        await self.redis_client.set(ticket_key, ticket_data, ex=settings.DOWNLOAD_TICKET_TTL)

        return ticket_uuid

    async def verify_and_prepare_download(
        self,
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
        ticket_data_raw = await self.redis_client.get(ticket_key)
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
        new_conn_count = await self.redis_client.incr(active_conns_key)
        if new_conn_count == 1:
            await self.redis_client.expire(active_conns_key, settings.DOWNLOAD_TICKET_TTL)

        # 5. 超過上限直接阻斷，不手動刪除或遞減，固定等 TTL 自動消亡
        if new_conn_count > settings.DOWNLOAD_TICKET_MAX_REQUESTS:
            raise TicketRateLimitError("該憑證的下載請求次數已達上限")

        # 6. 通過所有驗證後，呼叫既有業務邏輯校驗檔案狀態與磁碟完整性
        return await self.prepare_download(
            file_id=file_id,
            owner_id=owner_id
        )
