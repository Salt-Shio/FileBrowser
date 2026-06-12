# WSL2/Docker 環境下大檔案分塊上傳 Timeout 斷線問題

## 1. 問題發現與症狀 (Symptoms)
在使用 Vue + Vite + FastAPI (Docker on WSL2) 架構進行大檔案 (3.15 GB) 上傳測試時，遇到以下詭異症狀：
- **症狀**：前端將檔案切分為 2MB 的 Chunk 循序發送，上傳進度每次到了 **5% (約 150MB)** 左右，前端就會穩定跳出 `Network Error` 或 `Timeout`。
- **後端日誌**：後端並無任何 Crash 或 Exception 日誌，而是出現長達 16 秒的「請求死寂」，隨後前端宣告連線中斷。
- **最矛盾的變數**：
  - 在效能較弱的 **筆電 (Win 10, Ryzen 5 5600H)** 上：完美上傳至 100%。
  - 在效能較強的 **桌機 (Win 11, Ryzen 7 7700)** 上：必定在 10% 左右斷線崩潰。

---

## 2. 猜測的原因與驗證過程 (Speculated Causes & Debunking)

在尋找 Root Cause 的過程中，經歷了多次錯誤的推論與實驗：

### ❌ 錯誤猜測一：桌機速度太快，導致網路塞車 (Throughput Congestion)
* **推論**：認為 PC 的 CPU 處理與硬碟讀取過快，導致短時間內對 Docker 虛擬網路塞入過多 Request，撐爆了 Vite Proxy 或 Docker 內部的 Buffer。
* **驗證**：在前端強制加入 `50ms` 延遲，甚至用 Chrome DevTools 限制網速為「Fast 4G」。
* **結果 (打臉)**：用 Fast 4G 限制網速後，上傳速度慢到測到隔天早上都測不完，這種測試方法本身就毫無意義，根本無法有效驗證問題核心。

### ❌ 錯誤猜測二：SQLite 跨系統掛載引發 File Lock 延遲
* **推論**：由於 `/app/db` 是掛載到 Windows 本機，懷疑高頻率 (1500次) 對 SQLite 的 `UploadSession` 查詢，觸發了 WSL2 的 `9P` 檔案共享協定死鎖 (Deadlock)，導致後端 I/O 停頓超過 16 秒。
* **結果 (打臉)**：試圖讓 Redis 接管 Session 驗證來規避 SQLite，但被指出這嚴重破壞了原有的模組架構職責，且這只是一種「掩蓋問題的 Patch」，並非解決網路斷線的根本。

### ❌ 錯誤猜測三：Win 11 WSL2 網路對高頻短連線的耐受度比 Win 10 差
* **推論**：將問題歸咎於 Win 11 特有的 WSL2 `autoMemoryReclaim` 與新的 NAT 機制缺陷。
* **結果 (打臉)**：這被證實為缺乏官方文獻支持的過度推論（AI 幻覺），不能將查不出原因的 Bug 直接推卸給 OS 的底層玄學。

---

## 3. 真正的根因與解法 (Root Cause & Solution)

### 真正的根因：缺乏 Keep-Alive 導致的資源枯竭 (Port/Connection Exhaustion)
當傳送 3.15 GB 大檔、切分為 1500 個 Chunk 時，若 HTTP 沒有啟用 Keep-Alive，每一次上傳都會觸發一次完整的 `TCP 三次握手` 與 `四次揮手`。
在 WSL2 與 Docker 的 NAT 網路轉換層中，短時間內連續建立與銷毀數百個 TCP 短連線，極易引發底層虛擬網卡的連接埠枯竭 (Port Exhaustion) 或 Socket 狀態卡死，最終導致後續的連線請求直接被 Drop 掉，前端拋出 `ECONNRESET (Socket hang up)`。

### 解法：強制複用 TCP 連線
**1. 前端代理啟用 Keep-Alive**
在開發環境的 `vite.config.ts` 中，為 `http-proxy` 加入 `agent` 設定，強制 1500 個 Chunk 共用同一條 TCP 連線：
```typescript
import http from 'node:http'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 加入 Keep-Alive，閒置等待時間設為 10 秒
        agent: new http.Agent({ keepAlive: true, keepAliveMsecs: 10000 })
      }
    }
  }
})
```

**2. 匹配後端 Timeout (Keep-Alive Timeout Mismatch)**
Vite 代理預設將連線保留 10 秒，但 FastAPI 底層的 Uvicorn 預設 `timeout-keep-alive` 只有 **5 秒**。為了防止後端單方面提早踢掉連線導致前端錯愕斷線，需同步調大後端參數。
修改 `server/Dockerfile`：
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "15"]
```

### 總結
這個 Bug 教會我們：在處理高頻繁、切割傳輸的 I/O 作業時，**協定層的連線複用 (Connection Multiplexing / Keep-Alive)** 永遠是第一道、也是最關鍵的防線。任何不透過 Keep-Alive 的頻繁握手，最終都會在不可預期的底層網路環節遭到反噬。拒絕臨時解法 (Patch)，從架構本質下手才是正途。
