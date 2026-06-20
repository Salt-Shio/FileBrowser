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

    async def init_sparse_file(self, upload_id: str, total_size: int) -> None:
        file_path = os.path.join(self.temp_dir, f"{upload_id}.tmp")
        def _init():
            os.makedirs(self.temp_dir, exist_ok=True)
            with open(file_path, "wb") as f:
                f.truncate(total_size)
        await to_thread.run_sync(_init)

    async def finalize_file(self, upload_id: str) -> Dict[str, Any]:
        temp_path = os.path.join(self.temp_dir, f"{upload_id}.tmp")
        if not await to_thread.run_sync(os.path.exists, temp_path):
            raise FileNotFoundError(f"合併失敗：找不到暫存檔案 {upload_id}.tmp")

        file_uuid = str(uuid.uuid4())
        storage_name = f"{file_uuid}.dat"
        target_path = self.get_full_path(storage_name)

        def _finalize_logic():
            os.makedirs(self.upload_dir, exist_ok=True)
            
            # 讀取 .tmp 算 Hash (Python 3.11+ 專屬黑科技寫法)
            with open(temp_path, "rb") as source_f:
                digest = hashlib.file_digest(source_f, "sha256")
                sha256_hash_string = digest.hexdigest()
                
            current_size = os.path.getsize(temp_path)
            
            # 計算完 Hash 後，直接改名 (瞬間完成入籍)
            # 若是在同一個硬碟分區下，os.rename 不會發生真實的物理搬移
            os.rename(temp_path, target_path)
            
            return {
                "storage_name": storage_name,
                "size": current_size,
                "hash": sha256_hash_string
            }

        return await to_thread.run_sync(_finalize_logic)

    async def save_chunk(self, upload_id: str, offset: int, data: bytes) -> None:
        temp_path = os.path.join(self.temp_dir, f"{upload_id}.tmp")
        def _write():
            # 必須使用 r+b 模式，才能在不覆蓋原本內容的情況下任意寫入
            with open(temp_path, "r+b") as f:
                f.seek(offset)
                f.write(data)
        await to_thread.run_sync(_write)

    async def cleanup_temp(self, upload_id: str) -> None:
        temp_path = os.path.join(self.temp_dir, f"{upload_id}.tmp")
        if await to_thread.run_sync(os.path.exists, temp_path):
            await to_thread.run_sync(os.remove, temp_path)
