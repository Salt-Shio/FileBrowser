# Docker 掛載環境下 SQLite 混合模式與非法鎖定操作異常指南 (Database Exception Operation Bug)

在 Docker 容器化與 Windows 主機（Host）進行目錄掛載（Bind Mount）的開發環境下，使用 SQLite 作為資料庫極易因為「跨作業系統邊界」與「日誌模式不匹配」等非法操作，引發極難排查的無聲資料蒸發（Silent Data Rollback）及資料庫鎖死異常。

本文件旨在詳細剖析此 Bug 的成因、現象，並制定開發規範。

---

## 1. 核心成因解析

### 1.1 日誌模式不匹配 (Journal Mode Mismatch)
* **合法狀態**：容器內的 FastAPI 專案為了保證併發效能，開啟了 SQLite 的 **WAL (Write-Ahead Logging)** 模式。
* **非法操作**：本機（Windows 主機端）直接使用 Python 執行資料庫修改腳本（例如 `clean_sessions.py`）。由於未顯式設定，本機 Python 預設使用 **Rollback Journal (DELETE)** 模式連線並寫入。
* **衝突結果**：SQLite 官方規範禁止在同一個資料庫檔案上混合 WAL 與傳統日誌模式。本機以傳統模式寫入提交時，SQLite 為了防範損毀，會強行將容器端在寫入的 WAL 日誌**回滾並清除**，造成資料丟失。

### 1.2 跨 OS 共享記憶體 (mmap) 阻斷與日誌誤刪
* **SQLite 核心機制**：WAL 模式下，多個連線透過記憶體對映 (`mmap`) 共享 `.db-shm`（共享記憶體檔案）來感知彼此的連線狀態。當最後一個連線關閉時，SQLite 會將 `.db-wal` 內容合併回主資料庫，並將這兩個檔案刪除。
* **物理屏障**：Windows 主機與 Linux 容器（WSL2）**無法跨 OS 共享 `mmap` 的記憶體狀態**。
* **非法操作結果**：
  1. 本機腳本執行完畢呼叫 `conn.close()`。
  2. 本機 SQLite 讀取不到容器內連線的記憶體狀態，誤判自己為「最後一個關閉的連線」。
  3. 本機 SQLite 自動將掛載目錄下的 `.db-wal` 與 `.db-shm` 檔案**物理刪除**。
  4. 容器內的 FastAPI 進程此時仍持有這兩個檔案的 Handle（在 Linux 下，被刪除但仍開啟的檔案依然可以寫入，且不報錯）。
  5. 容器內所有的後續寫入均只寫到已刪除檔案的虛擬控制代碼中（API 回傳 200 OK，但其實並未落盤）。
  6. 當容器重啟時，控制代碼關閉，**寫入的資料無聲無息地徹底蒸發**。

### 1.3 WSL2 掛載點鎖定殘留 (Lock Leak)
* 當本機腳本或資料庫瀏覽器（如 DB Browser for SQLite）對資料庫進行讀寫時，會向 Windows 申請檔案鎖（File Lock）。
* 在 WSL2 掛載驅動下，Windows 的鎖定狀態釋放後，Linux 核心常發生鎖定狀態同步遲滯。
* 導致容器內連線時拋出：
  ```text
  sqlite3.OperationalError: unable to open database file
  ```
  （此時雖然可以使用 `cat` 等指令唯讀檔案，但 SQLite 因無法取得檔案鎖與寫入權限而拒絕連線）。

---

## 2. 異常現象對照表

| 現象 | 表現 | 原因 |
| :--- | :--- | :--- |
| **資料無聲蒸發** | Swagger 呼叫成功（如啟用 2FA、上傳檔案），但重啟容器後狀態變回 `False` 或檔案紀錄消失。整個過程無任何 Error Log。 | 本機腳本關閉時誤刪了 `.db-wal`，容器寫入到了 unlinked 的虛擬控制代碼中，重啟後被 Linux 核心清空。 |
| **資料庫無法開啟** | 容器內執行 API 拋出 `500`，或執行 python 查詢拋出 `sqlite3.OperationalError: unable to open database file`。 | 1. 實體 `.db-wal` 被本機刪除，容器判定損毀。<br>2. Windows 本機對該檔案仍持有鎖定，或 WSL2 發生鎖定殘留。 |

---

## 3. 開發規範與防範措施

### ⚠️ 禁止行為
在 FastAPI 容器正在執行期間，**禁止直接在本機（Host 端）使用非 WAL 模式的腳本或工具寫入資料庫**。

---

### 🛡️ 正確的開發測試排程（二選一）

#### 推薦方案 A：一律在 Docker 容器內執行腳本（最安全）
由於清理腳本在容器內執行時，與 FastAPI 共享同一個 Linux 核心與記憶體，SQLite 能完美感知彼此連線，絕不會發生誤刪：
```powershell
docker-compose exec server python server/scripts/clean_sessions.py
```

#### 備用方案 B：先停機、後清理、再開機
如果必須在本機執行 Python 腳本，請確實執行以下流程以釋放所有掛載鎖定：
```powershell
# 1. 停止容器服務，關閉所有連線
docker-compose stop server

# 2. 本機執行清理腳本
python server/scripts/clean_sessions.py

# 3. 啟動容器服務
docker-compose start server
```

---

### 💻 程式碼防禦手段

對於所有**有可能在本機或不同環境單獨執行**的資料庫腳本（如 `clean_sessions.py`），在連接資料庫後應**顯式宣告 WAL 模式**，避免因日誌模式不匹配引發回滾：

```python
import sqlite3

def run_db_operation(db_path):
    conn = sqlite3.connect(db_path)
    # 🟢 強制宣告為 WAL 模式，保持與容器一致，防止日誌模式衝突
    conn.execute("PRAGMA journal_mode=WAL")
    
    # 進行資料庫操作...
    cursor = conn.cursor()
    cursor.execute("DELETE FROM upload_sessions")
    
    conn.commit()
    conn.close()
```
