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

---

## 4. 2026-05-18: AnyIO `run_sync` 誤傳協程函式導致 GC 靜默失效問題 (Coroutine Silent Bypass)

### 📌 問題現象
* **狀況**：大掃除垃圾回收（GC）在運行時，本該檢查實體暫存資料夾是否存在，若過期則實體刪除；但測試中發現超時的物理目錄始終滯留，背景 GC 沒能成功超度物理孤立碎塊。

### 🔍 原因分析
1. 在舊版 VFS 業務底部實作的 GC 中，程式碼撰寫了非同步協程 `async def check_temp_dir_exists()`。
2. 但在呼叫時，將該協程函式傳給了執行緒池管理器：
   `await anyio.to_thread.run_sync(check_temp_dir_exists)`
3. **AnyIO 機制**：`run_sync` 專門用於將「同步阻塞函數（如 `os.path.exists`）」移交給背景執行緒池以防卡死 Event Loop。當傳入 `async def` 宣告的非同步函式時，背景執行緒直接執行該物件只會直接產生一個 `<coroutine>` 協程物件，而**不會去 `await` 它**。
4. 這導致協程內部的實體 `os.path.exists` 從未被真正調用。更致命的是，該協程物件在 Python 的 Boolean 條件判定中永遠為 `True`，導致 `temp_dir_exists` 判定恆為真，且底下的 `list_physical_dirs` 也跟著在未被 await 的協程中靜默打轉，GC 實體大掃除形同虛設。

### 🛠️ 解決方案
在 `app/gc/sentinel.py` 中，徹底廢除巢狀的 `async def` 輔助函數。將 Python 內建原生同步的 `os.path.exists` 直接傳入 `run_sync` 的第一個參數，並將輔助函數改為純同步形式傳入：
```python
# 🟢 同步輔助函數
def list_physical_dirs(path: str) -> list:
    return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

# 🟢 安全調用：傳入同步 os.path.exists 於第一個參數，引數作為第二個參數
temp_dir_exists = await anyio.to_thread.run_sync(os.path.exists, temp_dir)
if temp_dir_exists:
    physical_dirs = await anyio.to_thread.run_sync(list_physical_dirs, temp_dir)
```

### 🛡️ 預防方式
1. **嚴守 sync / async 邊界**：`anyio.to_thread.run_sync(func, *args)` 的第一個參數 `func` **必須且只能** 是常規的同步阻塞函式（如內建的 `os.*` 或 `shutil.*`），絕對不能傳入帶有 `async def` 的非同步協程函式。
2. **Event Loop 原生非同步**：我們自己寫的非同步業務（`async def` 宣告）應在主執行緒中直接使用 `await` 調用，無需丟入 thread pool。

---

## 5. 2026-05-18: 資料庫 Session 工廠名稱導入錯誤導致 Uvicorn 啟動崩潰 (ImportError)

### 📌 問題現象
* **狀況**：將 GC 排程移出並獨立為 `app/gc/sentinel.py` 重啟 Docker 伺服器後，容器不斷崩潰重啟，日誌丟出錯誤：
  ```text
  ImportError: cannot import name 'async_session_maker' from 'app.database' (/app/app/database.py)
  ```

### 🔍 原因分析
1. 在獨立重構 `sentinel.py` 時，憑空推測了資料庫會話工廠的名稱為 `async_session_maker` 並進行導入。
2. 然而，在 `app/database.py` 中，實際定義的非同步會話工廠名稱是 `AsyncSessionLocal = sessionmaker(...)`。
3. 由於未能先檢視實體檔案代碼就進行編寫，導致了命名不一致的靜態導入錯誤。

### 🛠️ 解決方案
檢視 `app/database.py` 的實體宣告，在 `app/gc/sentinel.py` 中將導入源與實例化名稱同步修正：
```python
# 修正後 (已修復)
from app.database import AsyncSessionLocal

# 實例化資料庫連接會話
async with AsyncSessionLocal() as db:
    res = await run_expired_uploads_gc(db)
```

### 🛡️ 預防方式
1. **落實「禁止推測」原則**：對於任何外部導入、未讀過的變數或資料庫 Session 工廠宣告，在撰寫代碼前**必須實打實地讀取實體宣告檔案**，嚴禁憑空猜想。
2. **靜態語法診斷**：在重啟或部署前，可在本地使用 IDE 或 `ruff check .` 進行語法拼字與導入檢驗，提早捕捉 ImportError。

---

## 6. 2026-05-19: 2FA 啟用狀態下仍可直接呼叫產生金鑰端點漏洞 (2FA Setup Regeneration Bypass)

### 📌 問題現象
* **狀況**：當使用者已經正式啟用 2FA 之後，直接訪問 `/2fa/generate` 產生金鑰端點，系統仍會成功產生新的 Base32 金鑰並寫入資料庫，且同時將 `is_totp_enabled` 設回 `False`。這導致已啟用的 2FA 被無條件覆蓋並繞過。

### 🔍 原因分析
1. 在 `AuthService.generate_2fa_setup` 中只檢查了使用者是否存在，並未校驗當前的 `user.is_totp_enabled` 狀態。
2. 因為該端點原先的設計是供「登入後但尚未啟用 2FA」的使用者首次產生綁定金鑰，但在已啟用狀態下若未加鎖定，會被惡意或誤觸調用，直接覆蓋現有的安全金鑰。

### 🛠️ 解決方案
在 `AuthService.generate_2fa_setup` 內部增加對 `user.is_totp_enabled` 的校驗。若為 `True`，直接拋出 `BaseBusinessException("已啟用 2FA，若要重新綁定請先停用舊的 2FA", status_code=400)`，要求必須先以舊 2FA 密鑰進行驗證並停用後才能重新綁定。

### 🛡️ 預防方式
1. **狀態機邊界檢查**：在實作任何有關安全狀態變更（例如啟用/禁用/重新產生 2FA 金鑰）的 API 時，必須明確定義狀態轉移規則。
2. **防範重設漏洞**：對於任何具有「重置」效果的敏感操作（如產生新金鑰），必須在進入時確認目前狀態是否已上鎖，若已上鎖，則必須強制先執行驗證與解鎖流程。

---

## 7. 2026-05-19: 虛擬節點軟刪除後物理磁碟檔案未被清除之儲存體洩漏問題 (Soft-Deleted Physical Files Storage Leak)

### 📌 問題現象
* **狀況**：當使用者對檔案或資料夾執行刪除操作（`/vfs/delete`）時，系統採用軟刪除（設定 `is_deleted = True` 與 `deleted_at = now`）。然而，被刪除檔案對應在 `/data/uploads` 底下的實體二進制檔案（如 `<uuid>.dat`）卻永遠殘留在磁碟上，且背景 GC 哨兵未對其進行任何盤點或清除，造成伺服器儲存空間的隱性洩漏（Storage Leak）。

### 🔍 原因分析
1. `VFSService.delete_node` 僅遞迴將檔案與資料夾的 `is_deleted` 標記為 `True`，未進行實體檔案移除以利未來可能實現的「資源回收桶」恢復機制。
2. 背景 GC 哨兵原先的設計只涵蓋了「未完成上傳的臨時碎片會話」與「物理孤立 temp 目錄」的盤點，遺漏了對資料庫中已確認軟刪除之「過期正式虛擬檔案與虛擬目錄」的物理與邏輯清除。

### 🛠️ 解決方案
在 GC 哨兵中新增 **Phase 3 清理邏輯刪除項目** 的處理階段：
1. 盤點所有 `is_deleted == True` 且 `deleted_at` 早於過期時間閾值（如 24 小時前）的 `File` 與 `Folder`。
2. 對於過期的 `File` 節點：先調用 `filesystem.delete_file` 執行實體檔案的物理刪除，隨後從資料庫刪除該 `File` 紀錄。
3. 對於過期的 `Folder` 節點：直接自資料庫刪除該 `Folder` 紀錄。由於已宣告的樹狀關係，SQLAlchemy 的 Unit of Work 會自動且安全地由內而外（子目錄 -> 父目錄）排序執行刪除。
4. 最終調用 `db.commit()` 送交資料庫交易。

### 🛡️ 預防方式
1. **軟刪除的生命週期閉環**：在使用「邏輯/軟刪除」設計模式時，必須同步設計與其配套的生命週期終點（Pruning/Purging）。應隨時審視：當資料不再被使用後，其實體資源（磁碟檔案、快取、關聯資料）是否能在生命週期結束時被自動安全回收。

