"""
實體檔案儲存模組 (Physical Storage)
職責：
1. 管理正式區 (/data/uploads) 的實體檔案
2. 提供實體路徑解析與檔案校驗
3. 執行實體檔案的物理刪除
4. 核心寫入邏輯：執行分塊合併與同步雜湊計算
"""
import os
import uuid
import hashlib
from typing import Dict, Any
from anyio import to_thread
from app.core.config import settings

# 路徑設定
UPLOAD_DIR = settings.UPLOAD_DIR
TEMP_DIR = settings.TEMP_DIR

def get_full_path(storage_name: str) -> str:
    """
    獲取實體檔案的絕對路徑
    """
    return os.path.join(UPLOAD_DIR, storage_name)

async def exists(storage_name: str) -> bool:
    """
    檢查實體檔案是否存在
    """
    path = get_full_path(storage_name)
    return await to_thread.run_sync(os.path.exists, path)

async def delete_file(storage_name: str) -> None:
    """
    物理刪除正式檔案
    """
    path = get_full_path(storage_name)
    if await to_thread.run_sync(os.path.exists, path):
        await to_thread.run_sync(os.remove, path)

async def merge_from_chunks(upload_id: str, total_chunks: int) -> Dict[str, Any]:
    """
    將暫存碎片合併為正式檔案 (Stitching)
    過程中同步計算 SHA256 與檔案大小
    """
    session_dir = os.path.join(TEMP_DIR, upload_id)
    file_uuid = str(uuid.uuid4())
    storage_name = f"{file_uuid}.dat"
    target_path = get_full_path(storage_name)

    def _merge_logic():
        sha256 = hashlib.sha256()
        current_size = 0
        
        # 確保目標目錄存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)
            
        with open(target_path, "wb") as target_f:
            for i in range(total_chunks):
                chunk_path = os.path.join(session_dir, str(i))
                if not os.path.exists(chunk_path):
                    raise FileNotFoundError(f"合併失敗：缺失分塊 {i}")
                
                with open(chunk_path, "rb") as source_f:
                    # 每次讀取由 settings 設定的緩衝區大小，以加速大檔案物理合併
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
