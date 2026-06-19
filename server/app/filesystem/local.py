import os
import uuid
import hashlib
import shutil
from typing import Dict, Any, List
from anyio import to_thread
from app.core.config import settings
from .base import BaseStorage

class LocalDiskStorage(BaseStorage):
    """
    本機硬碟儲存實作
    將原本 module 層級的函式封裝為物件導向實作。
    """
    def __init__(self):
        # 於建構時讀取設定檔，避免依賴外部全域狀態
        self.upload_dir = settings.UPLOAD_DIR
        self.temp_dir = settings.TEMP_DIR

    def get_full_path(self, storage_name: str) -> str:
        return os.path.join(self.upload_dir, storage_name)

    async def exists(self, storage_name: str) -> bool:
        path = self.get_full_path(storage_name)
        return await to_thread.run_sync(os.path.exists, path)

    async def delete_file(self, storage_name: str) -> None:
        path = self.get_full_path(storage_name)
        if await to_thread.run_sync(os.path.exists, path):
            await to_thread.run_sync(os.remove, path)

    async def merge_from_chunks(self, upload_id: str, total_chunks: int) -> Dict[str, Any]:
        session_dir = os.path.join(self.temp_dir, upload_id)
        file_uuid = str(uuid.uuid4())
        storage_name = f"{file_uuid}.dat"
        target_path = self.get_full_path(storage_name)

        def _merge_logic():
            sha256 = hashlib.sha256()
            current_size = 0
            
            # 確保目標目錄存在
            os.makedirs(self.upload_dir, exist_ok=True)
                
            with open(target_path, "wb") as target_f:
                for i in range(total_chunks):
                    chunk_path = os.path.join(session_dir, str(i))
                    if not os.path.exists(chunk_path):
                        raise FileNotFoundError(f"合併失敗：缺失分塊 {i}")
                    
                    with open(chunk_path, "rb") as source_f:
                        # 每次讀取由 settings 設定的緩衝區大小
                        while True:
                            buffer = source_f.read(settings.FILE_MERGE_BUFFER_SIZE)
                            if not buffer:
                                break
                            target_f.write(buffer)
                            sha256.update(buffer)
                            current_size += len(buffer)
            
            return {
                "storage_name": storage_name,
                "size": current_size,
                "hash": sha256.hexdigest()
            }

        return await to_thread.run_sync(_merge_logic)

    async def save_chunk(self, upload_id: str, index: int, data: bytes) -> None:
        session_dir = os.path.join(self.temp_dir, upload_id)
        if not os.path.exists(session_dir):
            await to_thread.run_sync(os.makedirs, session_dir, True)
        
        chunk_path = os.path.join(session_dir, str(index))
        def _write():
            with open(chunk_path, "wb") as f:
                f.write(data)
        await to_thread.run_sync(_write)

    async def list_chunks(self, upload_id: str) -> List[int]:
        session_dir = os.path.join(self.temp_dir, upload_id)
        if not await to_thread.run_sync(os.path.exists, session_dir):
            return []
        
        def _list():
            return [int(f) for f in os.listdir(session_dir) if f.isdigit()]
        return await to_thread.run_sync(_list)

    async def cleanup_temp(self, upload_id: str) -> None:
        session_dir = os.path.join(self.temp_dir, upload_id)
        if await to_thread.run_sync(os.path.exists, session_dir):
            await to_thread.run_sync(shutil.rmtree, session_dir)
