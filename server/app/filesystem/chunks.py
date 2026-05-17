"""
分塊暫存管理模組 (Chunk Management)
職責：
1. 管理分塊暫存目錄 (/data/temp)
2. 處理分塊數據的物理寫入
3. 清點現有分塊與清理會話資料
"""
import os
import shutil
from typing import List
from anyio import to_thread
from app.core.config import settings

# 路徑設定
TEMP_DIR = settings.TEMP_DIR

async def save_chunk(upload_id: str, index: int, data: bytes) -> None:
    """
    將分塊寫入暫存目錄
    """
    session_dir = os.path.join(TEMP_DIR, upload_id)
    if not os.path.exists(session_dir):
        await to_thread.run_sync(os.makedirs, session_dir, True)
    
    chunk_path = os.path.join(session_dir, str(index))
    def _write():
        with open(chunk_path, "wb") as f:
            f.write(data)
    await to_thread.run_sync(_write)

async def list_chunks(upload_id: str) -> List[int]:
    """
    獲取目前已上傳的分塊索引列表
    """
    session_dir = os.path.join(TEMP_DIR, upload_id)
    if not await to_thread.run_sync(os.path.exists, session_dir):
        return []
    
    def _list():
        return [int(f) for f in os.listdir(session_dir) if f.isdigit()]
    return await to_thread.run_sync(_list)

async def cleanup_temp(upload_id: str) -> None:
    """
    刪除暫存分塊目錄
    """
    session_dir = os.path.join(TEMP_DIR, upload_id)
    if await to_thread.run_sync(os.path.exists, session_dir):
        await to_thread.run_sync(shutil.rmtree, session_dir)
