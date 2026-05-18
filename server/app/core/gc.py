"""
背景垃圾回收哨兵模組 (Garbage Collection Sentinel)
職責：
1. 作為背景定時大掃除協程 (Daemon Task Runner)
2. 手動管理資料庫 AsyncSessionLocal 連線生命週期 (避免依賴注入缺失)
3. 提供極致的異常隔離與容錯防禦，確保哨兵永不崩潰 (Zero-Crash)
4. 在服務關閉時安全停止任務 (優雅退場)
"""
import asyncio
import logging
from app.database import AsyncSessionLocal
from app.services.vfs_service import VFSService
from app.core.config import settings

logger = logging.getLogger("gc_sentinel")

async def run_gc_sentinel():
    """
    背景定時垃圾回收哨兵：每隔固定時間 (預設 3600 秒) 自主喚醒，調用業務層大掃除。
    """
    logger.info("[GC] 垃圾回收背景守護哨兵已成功啟動！")
    
    try:
        while True:
            logger.info("[GC] 哨兵定時喚醒，即將發起雙向盤點大掃除...")
            
            # 每次循環手動建立非同步資料庫會話，確保生命週期完全獨立，防止連接洩漏
            async with AsyncSessionLocal() as db:
                try:
                    # 呼叫 VFS 執行層業務，處理 DB-driven 與 Physical-driven 大掃除
                    result = await VFSService.run_expired_uploads_gc(db)
                    if result["success"]:
                        logger.info(
                            f"[GC] 單次大掃除大成功！清除 DB 會話數: {result['db_cleaned']}，實體孤立目錄數: {result['physical_cleaned']}"
                        )
                    else:
                        logger.error(f"[GC] 單次大掃除部分出錯，錯誤詳情: {result['errors']}")
                except Exception as e:
                    # 異常隔離：任何大掃除內部的業務出錯，絕不向上拋出，保護排程器不崩溃
                    logger.critical(f"[GC] 垃圾回收業務執行時發生致命異常: {e}", exc_info=True)
            
            # 定時睡眠等待下個週期 (預設為 3600 秒)
            logger.info(f"[GC] 單次掃除完畢，進入睡眠。下個掃除週期將在 {settings.GC_INTERVAL_SECONDS} 秒後開啟...")
            await asyncio.sleep(settings.GC_INTERVAL_SECONDS)
            
    except asyncio.CancelledError:
        # 捕獲優雅退場訊號，安全向上拋出以配合 lifespan 的 await 收集
        logger.warning("[GC] 背景守護哨兵偵測到系統關閉訊號，即將優雅退出背景協程。")
        raise
    except Exception as e:
        # 保險起見：萬一發生不可預知的頂層錯誤，記錄日誌
        logger.critical(f"[GC] 哨兵協程發生未知頂層錯誤崩潰: {e}", exc_info=True)
