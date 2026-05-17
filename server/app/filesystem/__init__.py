"""
檔案系統功能模組 (Filesystem Infrastructure)
職責：
1. 作為物理磁碟操作的統一入口
2. 整合分塊管理 (chunks.py) 與實體存儲 (storage.py)
"""
from .chunks import (
    save_chunk,
    list_chunks,
    cleanup_temp
)
from .storage import (
    get_full_path,
    exists,
    delete_file,
    merge_from_chunks
)
