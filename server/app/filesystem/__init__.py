"""
檔案系統功能模組 (Filesystem Infrastructure)
職責：
1. 作為物理磁碟操作的統一入口
2. 整合 Storage OOP 介面 (Part 1 重構)
"""
from .base import BaseStorage
from .local import LocalDiskStorage
