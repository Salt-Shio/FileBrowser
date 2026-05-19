"""
垃圾回收守護哨兵 (App GC Sentinel)
職責：
1. 作為與 API 平級的「入口驅動層 (Entry Layer)」，負責定時大掃除維護。
2. 盤點資料庫中超時的活躍會話，並重用 VFSService.cancel_upload 釋放命名鎖定與磁碟分塊。
3. 盤點實體暫存目錄 (/data/temp) 中與資料庫脫鉤的物理孤立目錄，徹底清除。
4. 保持 strict 單向依賴流動 (gc/sentinel -> services/vfs_service -> filesystem)，避免循環引用。
"""
import os
import logging
import anyio
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models import UploadSession
from app.database import AsyncSessionLocal
from app.services.vfs_service import VFSService
from app import filesystem

logger = logging.getLogger("gc_sentinel")

# -----------------------------------------------------------------------------
# 模組最外層定義同步輔助函數，供 anyio.to_thread.run_sync 呼叫，提升效能
# -----------------------------------------------------------------------------
def list_physical_dirs(path: str) -> list:
    try:
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
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
# 垃圾回收大掃除執行單元
# -----------------------------------------------------------------------------
async def run_expired_uploads_gc(db: AsyncSession) -> dict:
    """
    執行垃圾回收大掃除 (優化扁平版：使用 Guard Clauses 降低巢狀縮排)
    """
    # 1. 計算時區安全的 Naive UTC 過期閾值
    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    expire_threshold = now_naive_utc - timedelta(hours=settings.UPLOAD_SESSION_EXPIRE_HOURS)
    
    db_cleaned_count = 0
    physical_cleaned_count = 0
    errors = []

    # --- 階段一：DB-driven 清理過期會話 ---
    try:
        stmt = select(UploadSession).where(UploadSession.created_at < expire_threshold)
        result = await db.execute(stmt)
        expired_sessions = result.scalars().all()

        # 🟢 Guard Clause: 若無任何過期會話，直接跳過
        if not expired_sessions:
            logger.info("[GC] 無任何過期資料庫會話紀錄，跳過 DB 清理。")
        else:
            logger.warning(f"[GC] 偵測到 {len(expired_sessions)} 個已過期上傳會話，即將進行清理...")
            for session in expired_sessions:
                try:
                    # 🔄 呼叫 VFSService 業務，實現代碼 100% 重用！
                    await VFSService.cancel_upload(db, upload_id=session.id, owner_id=session.owner_id)
                    db_cleaned_count += 1
                except Exception as err:
                    err_msg = f"清理過期會話 {session.id} 失敗: {err}"
                    logger.error(f"[GC] {err_msg}")
                    errors.append(err_msg)
    except Exception as e:
        err_msg = f"過期會話資料庫查詢失敗: {e}"
        logger.error(f"[GC] {err_msg}")
        errors.append(err_msg)

    # --- 階段二：Physical-driven 清理磁碟中的孤立暫存目錄 ---
    try:
        temp_dir = settings.TEMP_DIR
        # 🟢 修正：傳入原生同步 os.path.exists，交由執行緒池執行
        temp_dir_exists = await anyio.to_thread.run_sync(os.path.exists, temp_dir)

        # 🟢 Guard Clause 1: 若暫存目錄不存在，直接跳過物理清理
        if not temp_dir_exists:
            logger.info("[GC] 暫存目錄不存在，跳過物理大掃除。")
        else:
            # 🟢 傳入同步輔助函數 list_physical_dirs 取得子目錄列表
            temp_physical_dirs = await anyio.to_thread.run_sync(list_physical_dirs, temp_dir)

            # 🟢 Guard Clause 2: 若實體目錄為空，直接跳過
            if not temp_physical_dirs:
                logger.info("[GC] 實體暫存目錄為空，跳過物理大掃除。")
            else:
                active_stmt = select(UploadSession.id)
                active_result = await db.execute(active_stmt)
                active_ids = set(active_result.scalars().all())

                for tp_dir in temp_physical_dirs:
                    # 🟢 Guard Clause 3: 如果實體目錄在資料庫有活躍會話紀錄，說明是正常上傳，跳過！
                    if tp_dir in active_ids:
                        continue

                    p_path = os.path.join(temp_dir, tp_dir)
                    # 🟢 傳入同步輔助函數 get_dir_mtime 取得修改時間
                    mtime_stamp = await anyio.to_thread.run_sync(get_dir_mtime, p_path)
                    
                    # 🟢 Guard Clause 4: 若獲取修改時間失敗，可能目錄被佔用或不存在，跳過！
                    if not mtime_stamp:
                        continue

                    mtime = datetime.fromtimestamp(mtime_stamp, timezone.utc).replace(tzinfo=None)
                    
                    # 🟢 Guard Clause 5: 若該物理目錄最後修改時間在 24 小時內，說明是近期上傳，跳過！
                    if mtime >= expire_threshold:
                        continue

                    # 🌟 真正執行物理大掃除 (縮排大幅減至 4 層以內)
                    logger.warning(f"[GC] 偵測到物理孤立暫存目錄 {tp_dir} 且已超時，即將物理清除...")
                    try:
                        await filesystem.cleanup_temp(tp_dir)
                        physical_cleaned_count += 1
                    except Exception as err:
                        err_msg = f"物理清理孤立目錄 {tp_dir} 失敗: {err}"
                        logger.error(f"[GC] {err_msg}")
                        errors.append(err_msg)
    except Exception as e:
        err_msg = f"物理孤立暫存盤點失敗: {e}"
        logger.error(f"[GC] {err_msg}")
        errors.append(err_msg)


    logger.info(f"[GC] 垃圾回收大掃除完成！共清除 DB 會話: {db_cleaned_count} 個，磁碟孤立目錄: {physical_cleaned_count} 個")
    return {
        "db_cleaned": db_cleaned_count,
        "physical_cleaned": physical_cleaned_count,
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
