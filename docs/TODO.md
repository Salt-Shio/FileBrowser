# File Explorer - 後續規劃待辦清單 (TODO)

本文件紀錄了在 **Step 4.3: 檔案入籍工作流 (VFS Service Flow)** 實作完成後，系統的後續待辦任務與建議優化點。

---

## 🛠️ 後續階段規劃

### 1. Step 4.4: 串流下載與清理 (IO & Cleanup) [即將進行]
* **高效下載管道**：實作 `/vfs/download/{file_id}` 端點，利用 FastAPI 的 `FileResponse` 或是異步串流（StreamingResponse）以優化大檔案下載性能，同時保障擁有者身分權限。
* **背景碎片回收機制 (Garbage Collection, GC)**：
  - 當使用者上傳中斷且不再續傳時，暫存碎片會永久滯留在磁碟中。
  - **任務**：建立一個背景定時任務（如使用 `fastapi_utilities.repeat_every` 或 `apscheduler`），定時掃描並刪除資料庫中建立時間超過 24 小時的過期 `UploadSession`，並同步清理 `/data/temp/<upload_id>` 下的實體殘餘碎片。

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
