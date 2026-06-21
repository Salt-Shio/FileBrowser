"""
垃圾回收核心執行單元 (App GC Core Operations)
職責：
1. 階段一：直接物理與邏輯清理過期的上傳會話 (不經由 VFS Service 越權檢驗，高效批次提交)
2. 階段二：清理磁碟中的孤立暫存目錄 (/data/temp)
3. 階段三：物理與邏輯清除已過期的邏輯刪除檔案與目錄 (回收站過期清理)
"""
import os
import logging
import anyio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models import UploadSession, Folder, File
from app.filesystem.local import LocalDiskStorage

# 實例化儲存服務供背景 GC 使用
storage = LocalDiskStorage()

logger = logging.getLogger("gc_core")

import redis.asyncio as redis

# -----------------------------------------------------------------------------
# 同步輔助函數 (交由 anyio.to_thread.run_sync 於執行緒池執行)
# -----------------------------------------------------------------------------
def list_physical_temp_files(path: str) -> List[str]:
    try:
        return [f for f in os.listdir(path) if f.endswith('.tmp') and os.path.isfile(os.path.join(path, f))]
    except Exception as e:
        logger.error(f"[GC Helper] 讀取目錄 {path} 失敗: {e}")
        return []

def get_dir_mtime(path: str) -> Optional[float]:
    try:
        return os.path.getmtime(path)
    except Exception as e:
        logger.error(f"[GC Helper] 讀取目錄修改時間 {path} 失敗: {e}")
        return None

# -----------------------------------------------------------------------------
# 階段一：清理過期上傳會話
# -----------------------------------------------------------------------------
async def gc_expired_sessions(db: AsyncSession, redis_client: redis.Redis, expire_threshold: datetime) -> Tuple[int, List[str]]:
    """
    查詢並直接清理所有過期的上傳會話，物理清除暫存分塊，並自資料庫中抹除。
    加入 Redis 活躍防護：若 Redis 進度鎖仍在，代表活躍上傳中，則跳過並更新建立時間。
    """
    cleaned_count = 0
    errors = []
    
    try:
        stmt = select(UploadSession).where(UploadSession.created_at < expire_threshold)
        result = await db.execute(stmt)
        expired_sessions = result.scalars().all()

        if not expired_sessions:
            logger.info("[GC Phase 1] 無任何過期資料庫會話紀錄，跳過。")
            return 0, errors

        logger.warning(f"[GC Phase 1] 偵測到 {len(expired_sessions)} 個已過期上傳會話，開始 Redis 活躍防護校驗...")
        for session in expired_sessions:
            try:
                # 0. Redis 活躍防護：檢查是否有正在上傳的進度
                progress_key = f"vfs:upload_progress:{session.id}"
                is_active = await redis_client.exists(progress_key)
                if is_active:
                    # 活躍中，自動展延生命週期 (更新 created_at 到當前時間)，避免下次 GC 重複掃描
                    session.created_at = datetime.now(timezone.utc)
                    logger.info(f"[GC Phase 1] 會話 {session.id} 於 Redis 仍活躍，自動展延生命週期。")
                    continue
                # 1. 物理清除分塊暫存
                await storage.cleanup_temp(session.id)
                
                # 2. 直接刪除會話紀錄，不需重複執行資料庫 select 與越權校驗
                await db.delete(session)
                
                cleaned_count += 1
            except Exception as err:
                err_msg = f"物理/邏輯清理過期會話 {session.id} 失敗: {err}"
                logger.error(f"[GC Phase 1] {err_msg}")
                errors.append(err_msg)
        
        # 3. 批次一次性 commit，保存物理清理與生命週期展延的變更
        await db.commit()
            
    except Exception as e:
        err_msg = f"過期會話清理程序失敗: {e}"
        logger.error(f"[GC Phase 1] {err_msg}")
        errors.append(err_msg)
        
    return cleaned_count, errors

# -----------------------------------------------------------------------------
# 階段二：清理磁碟中的孤立暫存檔案 (.tmp)
# -----------------------------------------------------------------------------
async def gc_orphaned_temp_dirs(db: AsyncSession, expire_threshold: datetime) -> Tuple[int, List[str]]:
    """
    盤點暫存區 /data/temp 中的 .tmp 檔案，若實體檔案在資料庫中查無對應之會話，且已超時則物理清除。
    """
    cleaned_count = 0
    errors = []
    
    try:
        temp_dir = settings.TEMP_DIR
        temp_dir_exists = await anyio.to_thread.run_sync(os.path.exists, temp_dir)

        if not temp_dir_exists:
            logger.info("[GC Phase 2] 暫存目錄不存在，跳過物理大掃除。")
            return 0, errors

        temp_physical_files = await anyio.to_thread.run_sync(list_physical_temp_files, temp_dir)

        if not temp_physical_files:
            logger.info("[GC Phase 2] 實體暫存目錄為空或無 .tmp 檔案，跳過物理大掃除。")
            return 0, errors

        # 獲取所有活躍的上傳會話 ID 集合
        active_stmt = select(UploadSession.id)
        active_result = await db.execute(active_stmt)
        active_ids = set(active_result.scalars().all())

        for tp_file in temp_physical_files:
            # 取出 upload_id (移除 .tmp 副檔名)
            upload_id = tp_file[:-4]

            # 🟢 Guard Clause 1: 若此物理檔案在 DB 中有活躍會話，代表正常上傳中，跳過！
            if upload_id in active_ids:
                continue

            logger.warning(f"[GC Phase 2] 偵測到物理孤立暫存檔案 {tp_file} (查無活躍會話)，即將物理清除...")
            try:
                await storage.cleanup_temp(upload_id)
                cleaned_count += 1
            except Exception as err:
                err_msg = f"物理清理孤立檔案 {tp_file} 失敗: {err}"
                logger.error(f"[GC Phase 2] {err_msg}")
                errors.append(err_msg)
                
    except Exception as e:
        err_msg = f"物理孤立暫存盤點失敗: {e}"
        logger.error(f"[GC Phase 2] {err_msg}")
        errors.append(err_msg)
        
    return cleaned_count, errors

# -----------------------------------------------------------------------------
# 階段三：物理清理過期的邏輯刪除項目 (回收站過期物理清理)
# -----------------------------------------------------------------------------
async def gc_expired_soft_deleted_nodes(db: AsyncSession, expire_threshold: datetime) -> Tuple[int, int, List[str]]:
    """
    盤點並物理刪除已過期的邏輯刪除 (is_deleted == True) 檔案與目錄。
    """
    deleted_files_count = 0
    deleted_folders_count = 0
    errors = []
    
    try:
        # 1. 物理清理與 DB 抹除過期邏輯刪除的檔案
        stmt_files = select(File).where(File.is_deleted == True, File.deleted_at < expire_threshold)
        result_files = await db.execute(stmt_files)
        expired_files = result_files.scalars().all()

        if expired_files:
            logger.warning(f"[GC Phase 3] 偵測到 {len(expired_files)} 個已過期之邏輯刪除檔案，進行物理與 DB 清理...")
            for file_obj in expired_files:
                try:
                    # 先物理刪除
                    await storage.delete_file(file_obj.storage_path)
                    # 再 DB 刪除
                    await db.delete(file_obj)
                    deleted_files_count += 1
                except Exception as err:
                    err_msg = f"物理清理刪除檔案 {file_obj.id} 失敗: {err}"
                    logger.error(f"[GC Phase 3] {err_msg}")
                    errors.append(err_msg)

        # 2. DB 抹除過期邏輯刪除的目錄
        stmt_folders = select(Folder).where(Folder.is_deleted == True, Folder.deleted_at < expire_threshold)
        result_folders = await db.execute(stmt_folders)
        expired_folders = result_folders.scalars().all()

        if expired_folders:
            logger.warning(f"[GC Phase 3] 偵測到 {len(expired_folders)} 個已過期之邏輯刪除目錄，進行 DB 清理...")
            for folder_obj in expired_folders:
                try:
                    await db.delete(folder_obj)
                    deleted_folders_count += 1
                except Exception as err:
                    err_msg = f"清理刪除目錄 {folder_obj.id} 失敗: {err}"
                    logger.error(f"[GC Phase 3] {err_msg}")
                    errors.append(err_msg)

        # 3. 統一批次 commit 異動 (移除 if 條件以保持一致性與未來擴充安全)
        await db.commit()
            
    except Exception as e:
        err_msg = f"邏輯刪除項目盤點與物理清理失敗: {e}"
        logger.error(f"[GC Phase 3] {err_msg}")
        errors.append(err_msg)
        
    return deleted_files_count, deleted_folders_count, errors
