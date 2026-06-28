# Nginx Proxy Manager (NPM) 反向代理架構與原理紀錄

這份文件記錄了將應用程式透過 Tailscale 部署上線時，關於 Nginx Proxy Manager (NPM) 與 Cloudflare 的設定細節與核心運作原理。

## 1. 基礎設施架構全貌
流量的傳遞路徑如下：
1. **使用者 (Browser)**：輸入 `https://nas.salt-shio.win`
2. **Cloudflare DNS**：將網址解析為 Tailscale 的私有 IP (`100.x.x.x`)。*(注意：小橘雲必須設定為灰色 DNS Only，以免 CF 試圖代理私有 IP 導致失敗)*。
3. **Tailscale 虛擬網卡**：將加密封包安全地傳送到 Linux 伺服器。
4. **Nginx Proxy Manager (NPM)**：作為「總機」，在 Port 443 接收流量，卸載 SSL 加密，並決定要把流量轉發給內部哪一個 Docker 容器。
5. **Docker 內部網路**：透過內部 DNS 解析，找到目標容器並傳遞 HTTP 流量。

## 2. 憑證申請：DNS-01 Challenge 的必要性
* **痛點**：因為伺服器位於 Tailscale 內網 (`100.x` IP)，Let's Encrypt 無法從外部公網連線到我們的 80 Port 進行 HTTP 驗證。
* **解法**：使用 DNS-01 Challenge。我們產生了一組 Cloudflare API Token (權限：`Zone -> DNS -> Edit`) 給 NPM。
* **運作機制**：NPM 會自動拿著 Token 去 Cloudflare 新增一筆特定的 TXT DNS 紀錄。Let's Encrypt 驗證該 DNS 紀錄無誤後，便會核發 HTTPS 綠色鎖頭憑證。
* **雷點紀錄**：在申請時遇到 `Internal Error`，根本原因是**未將 NPM 預設的聯絡信箱 (`admin@example.com`) 改為真實信箱**，導致 Let's Encrypt API 拒絕核發憑證。

## 3. Proxy Host 核心設定原理

### Forward Hostname (Docker 內部 DNS)
* **設定值**：`file-explorer-server` (Port `8000`)
* **原理**：我們不需要綁定實體的內部 IP (如 `192.168.x.x`)，而是直接使用 Docker Compose 中定義的容器名稱。這是因為 Docker 在啟動容器時，會建立一個與世隔絕的區域網路 (Bridge Network)，並內建一台 DNS 伺服器。這台 DNS 會自動將容器名稱解析為對應的動態內部 IP，實現完美的「服務發現 (Service Discovery)」。

### Scheme 設定為 `http` (SSL 卸載 / SSL Offloading)
* **為何不選 HTTPS？**：從使用者的瀏覽器到 NPM (大門口) 的這段路徑是危險的公網，所以我們使用 HTTPS 加密。但從 NPM 到 Python 後端容器的這段路徑，是發生在 Linux 機器內部安全的 Docker 虛擬網路中。
* 對內繼續使用 HTTPS 不僅會白白浪費 CPU 算力進行重複加解密，且後端容器也沒有配置內部 SSL 憑證，強制使用 HTTPS 會導致 `502 Bad Gateway`。這稱為 SSL 卸載。

### Force SSL 與 Cache Assets
* **Force SSL**：這是在約束外部連線。若打開，NPM 只要收到 HTTP (Port 80) 的請求，就會自動回傳 `301 Redirect`，強制瀏覽器改用安全的 HTTPS (Port 443) 重新連線。
* **Cache Assets**：這是 Nginx 的靜態資源快取。建議在開發期間保持**關閉**，避免程式碼更新後，瀏覽器卻依然讀取到 NPM 快取中的舊畫面，徒增除錯困難。正式上線後可開啟以提升載入速度。
