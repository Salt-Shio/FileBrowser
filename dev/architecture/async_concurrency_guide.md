# Python 非同步與並發開發指南 (Async & Concurrency Guide)

這份文件旨在說明在 FastAPI 等非同步框架中，如何正確使用非同步 (Async) 與多執行緒 (Multi-threading)，以及各個核心關鍵字的具體運作原理與差異。

## 核心觀念：單一服務生與廚房
想像 Python 的事件迴圈（Event Loop）是一家餐廳裡的「唯一一位超級服務生」（主執行緒）。
- **非同步 (Async/Await)**：服務生點餐後，不用在廚房門口等，可以先去服務其他桌。這是在**同一個執行緒**內快速切換。
- **多執行緒 (Thread Pool)**：有些任務需要服務生自己動手做（例如去倉庫算庫存、搬重物），這會導致整間餐廳停擺（無法接新的 API 請求）。這時候必須把這件工作外包給「後台的切菜工」（Worker Threads）。

---

## 關鍵字與函數詳解

### 1. `async` / `await`
這是 Python 原生非同步的基礎語法，用來在單一執行緒中實現高並發。

- **`async def`**：用來定義一個「非同步函數（協程 Coroutine）」。這只是告訴 Python 這個函數**可以**被暫停和恢復，但它不會自動變成背景執行。
- **`await`**：這是一個「交出控制權」的動作。當服務生遇到 `await` 時，他會把目前的狀態存起來，轉身去處理其他任務，直到等待的事情（例如資料庫回傳結果）完成了，他才會回來繼續往下走。
  - **適用情境**：I/O 操作（網路請求、非同步資料庫查詢）。
  - **注意**：只能在 `async def` 裡面使用 `await`。

### 2. `anyio.sleep` (或 `asyncio.sleep`)
原生支援非同步的「等待」函數。

- **運作原理**：它會告訴事件迴圈：「請設定一個鬧鐘，在 N 秒後叫醒我，這段時間你可以去做其他事」。
- **與 `time.sleep` 的致命差異**：
  - `time.sleep(5)`：服務生站在原地發呆 5 秒，**整間餐廳停擺**（絕對禁止在 Async 框架中使用，會卡死整個 API 伺服器）。
  - `await anyio.sleep(5)`：服務生設定 5 秒鬧鐘，然後去服務其他上千個客人，5 秒後再回來。

### 3. `asyncio.create_task`
用來產生「背景任務」。

- **運作原理**：將一個 `async def` 函數包裝成任務，立刻丟進事件迴圈的排程中，**不會卡住當前的程式碼往下執行**。它與主程式平行運作（交錯執行）。
- **適用情境**：啟動背景常駐服務（例如我們的 GC 哨兵）、發送不需等待結果的 Email 或通知。
- **安全守則**：建立 Task 後，請務必將它存進一個全域變數（例如 `app.state.gc_task = task`）。否則它會變成孤兒行程（Orphan Task），導致程式關閉時無法被優雅取消（呼叫 `task.cancel()`），甚至引發記憶體洩漏。

### 4. `anyio.to_thread.run_sync` (或 `asyncio.to_thread`)
用來解決「會卡死主執行緒的同步函數」。

- **運作原理**：將一個傳統的同步函數，打包丟給背後由 Python 管理的「執行緒池（Thread Pool）」去執行。主執行緒透過 `await` 等待它完成，這樣主執行緒就能趁機去接其他的 API 請求。
- **適用情境**：
  - 傳統硬碟操作：`os.listdir`、`os.path.exists`、`shutil.rmtree`、`os.path.getmtime` 等。
  - 輕量級 CPU 運算：密碼雜湊 (`bcrypt`, `argon2`)。
  - 不支援 Async 的舊套件：例如 `requests.get`。
- **為什麼要用**：因為硬碟讀寫很慢，且這些操作沒有原生的 `await` 支援，如果不丟給 Thread 處理，唯一的服務生就會被迫親自去搬磚，導致伺服器效能大跌。

---

## 判斷決策樹：我該用哪種方法？

1. **這個操作有支援 Async (可以 await) 嗎？**
   - 有支援（如 `asyncpg`, `httpx`） ➔ 直接用 `await`。
2. **沒有支援 Async，是操作本地硬碟或第三方同步套件嗎？**
   - 是 ➔ 用 `await anyio.to_thread.run_sync(...)` 丟給獨立執行緒處理。
3. **這是一個需要永遠在背景跑的無窮迴圈嗎？**
   - 是 ➔ 在啟動時用 `asyncio.create_task(...)` 掛載。

---

## 範例：完美的結合

在我們的 GC 哨兵程式中，這三者完美結合在一起：

```python
async def run_gc_sentinel():
    # 這個函數是被 main.py 用 `asyncio.create_task(run_gc_sentinel())` 在背景啟動的
    while True:
        # 1. 原生非同步：打資料庫，遇到 I/O 會自動交出控制權，不卡死
        async with AsyncSessionLocal() as db:
            await db.execute(...) 
            
        # 2. 同步硬碟操作：這會卡死主執行緒！必須外包給 Thread 去做
        file_exists = await anyio.to_thread.run_sync(os.path.exists, "/data/temp")
        
        # 3. 原生非同步等待：設定計時器，服務生去接其他 API 請求
        await anyio.sleep(3600)
```
