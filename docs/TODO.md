# File Explorer - 後續規劃待辦清單 (TODO)

本文件紀錄了在 **Step 4.3: 檔案入籍工作流 (VFS Service Flow)** 實作完成後，系統的後續待辦任務與建議優化點。

---

## 🛠️ 後續階段規劃

### 1. Step 4.4: 串流下載與清理 (IO & Cleanup) [已完成 100%]
* **高效下載管道**：已實作 `/vfs/download/{file_id}` 端點，利用 FastAPI 的 `FileResponse` 保障擁有者身分權限，並完整支援安全 ETag 快取校驗與 Range 斷點續傳。
* **背景與主動碎片回收機制 (GC & Active Cancel)**：
  - **定時背景哨兵 (GC)**：已實作獨立 `app/gc/sentinel.py` 包，定時盤點清理過期會話與物理孤立目錄，並安全掛載於 `main.py` lifespan 中。
  - **主動取消 API**：已實作 `/vfs/upload/cancel`，前端可隨時主動釋放命名鎖定並物理清空碎片。
  - **上傳進度探測 API**：已實作 `/vfs/upload/status/{upload_id}`，支援斷線重連差集續傳。

### 1.1 背景哨兵 (GC) 的後續優化方向 [未來規劃]
* **磁碟容量耗盡防禦聯動**：GC 哨兵在掃描時，若發現磁碟剩餘空間低於安全值（如 5%），可主動提升掃描頻率，或優先清理部分未滿 24 小時但進度停滯的會話。
* **分散式鎖或進程互斥 (Locking)**：若未來採用多實例部署（如多容器負載均衡），應避免多個哨兵同時掃描同一塊資料庫，可引入 Redis 分散式鎖或資料庫行級鎖限制執行。

### 2. Phase 5: 輔助系統與處理 (Media Processor)
* **非同步媒體處理器**：
  - 對於已上傳的圖片與影片，設計非同步工作流（Celery / BackgroundTasks）。
  - 自動生成圖片縮圖 (Thumbnails) 並提取 EXIF 元數據，提升 VFS 瀏覽體驗。

### 3. Phase 6: 系統完善與管理 (Admin & Polish)
* **安全自帶綁定**：實作前端密碼修改與使用者 2FA (TOTP) 綁定流程，提供高度安全的個人管理後台。

---

## 🔒 安全性與效能優化 (Security & Performance Optimizations)

### 1. 磁碟容量耗盡防禦 (Disk Exhaustion Protection)
* **背景**：惡意使用者如果透過 API 惡意建立大量 `UploadSession` 並重複寫入二進制碎片，可能導致伺服器磁碟空間耗盡 (DoS 攻擊)。
* **優化建議**：
  - 在 `init_upload()` 中，限制單一使用者同時擁有的活躍會話總數（例如最多 3 個活躍會話）。
  - 在 `upload_chunk()` 寫入前，增加磁碟剩餘空間檢查，若空間低於安全值（如 5%）應停止寫入並拋出異常。
  - 對單個檔案設定最大上限（如最大 5GB），防範極大檔案上傳。

### 2. 重複合併防護 (Idempotency in Finalization)
* **背景**：當前端因網路震盪，針對同一個會話發送兩次 `/finalize` 請求時，可能會造成競態條件 (Race Condition)。
* **優化建議**：
  - 在 `finalize_upload()` 中使用分散式鎖（或在資料庫使用 `SELECT FOR UPDATE`），在開始合併前，先將 `UploadSession` 標記為 `processing`，阻止併發結算。
