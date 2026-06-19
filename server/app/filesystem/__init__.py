"""
檔案系統功能模組 (Filesystem Infrastructure)
職責：
1. 作為物理磁碟操作的統一入口
2. 整合 Storage OOP 介面 (Part 1 重構)
"""
from .base import BaseStorage
from .local import LocalDiskStorage

# 暫時的全域單例，讓舊的 vfs_service.py 與 api/vfs.py 不用改 code 就能運作
# TODO: (Phase 9 Part 3) 待 Service 層實作 DI 之後，拔除此全域變數與代理函數
storage_instance = LocalDiskStorage()

get_full_path = storage_instance.get_full_path
exists = storage_instance.exists
delete_file = storage_instance.delete_file
merge_from_chunks = storage_instance.merge_from_chunks
save_chunk = storage_instance.save_chunk
list_chunks = storage_instance.list_chunks
cleanup_temp = storage_instance.cleanup_temp
