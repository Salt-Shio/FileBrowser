# 專案 Bug 紀錄與學習手冊 (Error Log & Learnings)

本文件紀錄了開發過程中遇到的 Bug，包含原因分析、解法、以及如何預防，供團隊與 AI 協同開發時參考，避免重蹈覆轍。

---

## 1. 2026-05-18: SQLAlchemy AsyncSession 刪除會話未生效問題 (UploadSession Leftover)

### 📌 問題現象
* **狀況**：進行大檔案分塊上傳時，前兩次上傳皆成功入籍 VFS 虛擬檔案系統並物理合併，但 `upload_sessions` 資料表中的舊會話資料卻沒有被刪除（殘留在資料庫中）。
* **日誌警告**：
  ```text
  /app/app/services/vfs_service.py:557: RuntimeWarning: coroutine 'AsyncSession.delete' was never awaited
    db.delete(session)
  RuntimeWarning: Enable tracemalloc to get the object allocation traceback
  ```

### 🔍 原因分析
1. 在 SQLAlchemy 2.0 中，使用非同步模式 (`AsyncSession`) 時，`db.delete(instance)` 是一個**非同步協程（Coroutine）**，必須使用 `await` 來調用。
2. 原先程式碼在 `finalize_upload` 階段寫成了 `db.delete(session)`，**漏掉了 `await`**，導致 Python 只是建立了協程物件，卻從未將刪除 SQL 語句實際發送至 SQLite 資料庫執行。
3. 由於漏加 `await` 是語法運行時的 Coroutine 警告，並不會引起請求崩潰，因此 API 依然返回了 200 OK，使得 Bug 非常隱蔽。

### 🛠️ 解決方案
在 `app/services/vfs_service.py` 檔案的 `finalize_upload` 函式中，為刪除會話的語句補上 `await` 關鍵字：

```python
# 修改前
db.delete(session)
await db.commit()

# 修改後 (已修正)
await db.delete(session)
await db.commit()
```

修改完成後，重新啟動 Docker 伺服器容器，使最新的 Python 字節碼在記憶體中生效。

### 🛡️ 預防方式
1. **靜態程式碼檢查**：在 CI 流程或本地編輯器中啟用強大的 Linter（如 `Ruff` 或 `Pylint`），以偵測「未被 awaited 的協程（unawaited coroutines）」。
2. **開發習慣**：使用非同步 SQLAlchemy（`AsyncSession`）時，請時刻保持警覺：`db.delete()`、`db.commit()`、`db.refresh()`、`db.execute()` 皆為非同步函式，一律必須加上 `await`。
3. **Docker 開發注意**：如果在本地修改了代碼但測試時沒有反應，請務必先執行 `docker-compose restart server` 以重啟容器，確保容器記憶體中的 Python 程序重載了最新的代碼。

---

## 2. 2026-05-18: Windows 本地指令腳本中文輸出與 Emoji 導致的 `cp950` 編碼異常

### 📌 問題現象
* **狀況**：在 Windows 本地終端機執行清理懸空會話的輔助 Python 腳本 `clean_sessions.py` 時崩潰：
  ```text
  UnicodeEncodeError: 'cp950' codec can't encode character '\U0001f9f9' in position 0: illegal multibyte sequence
  ```

### 🔍 原因分析
1. Windows CMD/PowerShell 在中文地區預設使用 `CP950` (繁體中文 Big5) 作為終端機字元編碼，而非系統全局的 UTF-8。
2. 腳本中的 `print()` 包含了 `🧹` 等特殊 Emoji 圖示以及部分中文字元，在 CP950 編碼表下找不到對應的字元，因而導致 Python 的標準輸出流（stdout）丟出無法編碼的 runtime 錯誤。

### 🛠️ 解決方案
1. 將輔助腳本 `clean_sessions.py` 的控制台輸出（`print` 語句）全面修改為安全且兼容性極佳的 **純英文字元（ASCII）**，移除了所有 Emoji。
2. 這能確保腳本在 Windows CMD、Linux 終端、或是 Docker CLI 下執行時皆有 100% 的兼容性。

### 🛡️ 預防方式
1. 撰寫作為「本地運作」的跨平台命令列輔助腳本時，盡量避免直接輸出繁複的 unicode/emoji 特殊符號。
2. 如果一定要輸出，則需在 Python 檔案頭進行 sys 輸出編碼強設或使用英文字串作為首選。

---

## 3. 2026-05-18: 整合測試腳本斷言邊界硬編碼導致的 False-Alarm 錯誤

### 📌 問題現象
* **狀況**：執行斷點續傳測試腳本 `test_resume_upload.py` 時，在探測 API 回傳時丟出斷言失敗：
  ```text
  ❌ [狀態探測錯誤] 伺服器回傳的分塊狀態不符預期，終止測試。
  ```
  而此時伺服器實際上回傳了正確的已收與缺漏分塊差集。

### 🔍 原因分析
1. 測試檔案的大小隨機產生，且檔頭增加了動態前綴位元組，導致總大小微幅上升為 15.7MB，在 `3MB` 分塊下進位為 **6 個分塊**。
2. 但測試腳本卻硬編碼斷言缺失分塊陣列必須剛好等於 `[2, 3, 4]`（以 5 個分塊為前提假設），導致與伺服器誠實且正確計算出的 `[2, 3, 4, 5]` 發生不符，引發了測試的 False-Alarm（虛警）。

### 🛠️ 解決方案
在測試腳本中，將斷言修改為**動態計算**：
```python
expected_missing = list(range(2, total_chunks))
if uploaded == [0, 1] and missing == expected_missing:
    ...
```
這能讓測試腳本在任何檔案大小與分片數量下，都能完美完成進度差集校驗！

### 🛡️ 預防方式
1. 撰寫整合或單元測試的 Mock 斷言時，**切忌硬編碼預期值**。
2. 應該依據上游變量（如本例中的 `total_chunks`）動態計算出預期邊界值，使測試兼具靈活性與健壯度。
