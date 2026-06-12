"""
垃圾回收守護哨兵 (App GC Sentinel)
職責：
1. 作為與 API 平級的「入口驅動層 (Entry Layer)」，負責定時大掃除維護。
2. 定期調用 app.gc.core 各清理階段，保持背景任務的高效與安全。
3. 保持 strict 單向依賴流動 (gc/sentinel -> gc/core -> database/filesystem)，無循環引用，不依賴 VFS 服務層。
"""
import logging
import anyio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.gc.core import (
    gc_expired_sessions,
    gc_orphaned_temp_dirs,
    gc_expired_soft_deleted_nodes
)

logger = logging.getLogger("gc_sentinel")

# -----------------------------------------------------------------------------
# 垃圾回收大掃除執行單元
# -----------------------------------------------------------------------------
async def run_expired_uploads_gc(db: AsyncSession) -> dict:
    """
    執行垃圾回收大掃除 (調度核心：調用分開的 GC 清理模組)
    """
    # 1. 計算時區安全的 Naive UTC 過期閾值
    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    expire_threshold = now_naive_utc - timedelta(hours=settings.UPLOAD_SESSION_EXPIRE_HOURS)
    
    errors = []

    # --- 階段一：清理過期上傳會話 ---
    db_cleaned_count, errs1 = await gc_expired_sessions(db, expire_threshold)
    errors.extend(errs1)

    # --- 階段二：清理磁碟中的孤立暫存目錄 ---
    physical_cleaned_count, errs2 = await gc_orphaned_temp_dirs(db, expire_threshold)
    errors.extend(errs2)

    # --- 階段三：物理清理過期的邏輯刪除項目 (Files & Folders) ---
    deleted_files_count, deleted_folders_count, errs3 = await gc_expired_soft_deleted_nodes(db, expire_threshold)
    errors.extend(errs3)

    logger.info(f"[GC] 垃圾回收大掃除完成！共清除 DB 會話: {db_cleaned_count} 個，磁碟孤立目錄: {physical_cleaned_count} 個，物理刪除檔案: {deleted_files_count} 個，刪除目錄: {deleted_folders_count} 個")
    return {
        "db_cleaned": db_cleaned_count,
        "physical_cleaned": physical_cleaned_count,
        "deleted_files": deleted_files_count,
        "deleted_folders": deleted_folders_count,
        "success": len(errors) == 0,
        "errors": errors
    }

# -----------------------------------------------------------------------------
# 定時背景排程哨兵
# -----------------------------------------------------------------------------
async def run_gc_sentinel():
    """
    定時定週期掃描背景垃圾回收守護協程
    """
    logger.info("[GC] 垃圾回收背景守護哨兵已成功啟動！")
    while True:
        try:
            logger.info("[GC] 開始執行定時垃圾回收盤點...")
            async with AsyncSessionLocal() as db:
                res = await run_expired_uploads_gc(db)
                logger.info(f"[GC] 盤點結果: {res}")
            
            # 盤點完成後，根據 settings 裡配置的週期進行非同步睡眠
            await anyio.sleep(settings.GC_INTERVAL_SECONDS)
        except anyio.get_cancelled_exc_class():
            logger.warning("[GC] 背景哨兵收到取消信號，正在優雅退出...")
            break
        except Exception as e:
            logger.error(f"[GC] 哨兵循環發生非預期異常: {e}")
            # 發生異常時也稍微等待，避免無窮迴圈暴走
            await anyio.sleep(5)
