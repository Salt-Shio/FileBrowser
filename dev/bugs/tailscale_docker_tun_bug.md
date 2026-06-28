# Tailscale Docker 啟動失敗 (`signal: killed` & `--tun=userspace-networking`)

## 1. 錯誤現象與症狀
在 `docker-compose.yml` 啟動 Tailscale 容器時，容器內部不斷重啟並發送 `SIGTERM` 殺死程序。
這會導致使用者在網頁端即使點選授權成功，Tailscale 仍舊立刻變成 Offline (離線) 或被標記為 Ephemeral，完全無法順利拿到 IP。

日誌中出現以下兩個關鍵錯誤：
- `Program starting: ... "--tun=userspace-networking"`
- `failed to auth tailscale... tailscale up failed: signal: killed`

補充 Ephemeral 處理方式
```yaml
environment:
  - TS_STATE_DIR=/var/lib/tailscale # 強制將登入狀態寫入硬碟，避免變成免洗機器
```


## 2. 根本原因 (Root Cause)
這個 Bug 發生的根本原因在於 Docker Compose 中對硬體裝置的**錯誤掛載寫法**。
在 `docker-compose.yml` 裡面，誤將 `/dev/net/tun` 寫在了 `volumes` (資料夾掛載) 之下：

```yaml
# ❌ 引發 Bug 的錯誤設定：
    volumes:
      - ./tailscale-data:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun  
```

因為寫在 `volumes` 裡，Docker 把它當成了普通的資料夾，於是在容器內部的 `/dev/net/` 創建了一個名為 `tun` 的**空白資料夾**。
當 Tailscale 核心程式啟動時，它試圖去讀取實體的虛擬網卡，卻摸到一個假資料夾。
Tailscale 為了自救，被迫降級啟動 `userspace-networking` (模擬網路)。
然而，由於設定檔中還指定了 `network_mode: host`，**「實體主機網路」與「模擬網路」產生嚴重的架構衝突 (Deadlock)**。這導致內部啟動腳本執行 `tailscale up` 時一直卡住超時，最後由啟動腳本自己觸發 `SIGTERM` 訊號強制殺死程序。

## 3. 解決方案 (Solution)
必須將 `/dev/net/tun` 從 `volumes` 移到 **`devices`** 區塊下，確保 Docker 傳遞的是真正的硬體裝置節點 (Character Device)：

```yaml
# ✅ 正確的修復寫法：
    devices:
      - /dev/net/tun:/dev/net/tun  # 將 TUN 裝置傳入
    volumes:
      - ./tailscale-data:/var/lib/tailscale
```

修正完畢後，執行 `docker compose up -d --force-recreate tailscale` 重建容器，Tailscale 就能順利讀到網卡，不會再降級，也不會再因為死鎖被 killed 了。
