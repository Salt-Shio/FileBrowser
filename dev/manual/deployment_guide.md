# 私有雲終極型態 - 部署與設定指南

這份指南將手把手帶你完成 **Tailscale + Cloudflare DNS + Nginx Proxy Manager** 的完整部署流程。因為這部分幾乎都是**你個人的帳號設定與環境搭建**，所以我幫你整理成以下 5 個明確的實作步驟。

---

## 🟢 Step 1: 基礎網路打通 (Tailscale)
首先，我們要先確保你的伺服器（架設 File Explorer 的那台電腦）和你的筆電/手機，都在同一個虛擬區網內。

1. **伺服器端安裝**：在伺服器上下載並安裝 Tailscale，登入你的帳號。
2. **獲取私有 IP**：在伺服器上打開 Tailscale，記下分配給這台機器的 IP（通常開頭是 `100.x.x.x`）。這非常重要，這就是我們未來的專屬連線地址。
3. **客戶端安裝**：在你要用來瀏覽網頁的筆電或手機上，也安裝 Tailscale 並登入同一個帳號。

---

## 🟢 Step 2: 網域綁定與 API 權杖 (Cloudflare)
接下來我們要設定網域，並拿到一把讓伺服器能自動申請 HTTPS 憑證的「鑰匙」。

1. **設定 DNS 解析**：
   - 登入 Cloudflare 後台，點進你的網域。
   - 進入左側選單的 **「DNS」->「紀錄」**。
   - 點擊 **「新增紀錄」**：
     - **類型**：`A`
     - **名稱**：填入你想要的子網域（例如 `files`）
     - **IPv4 位址**：填入你剛剛抄下來的 **Tailscale IP (`100.x.x.x`)**。
   - > [!WARNING]
     > **代理狀態 (Proxy status)**：請務必點擊雲朵圖示將其**關閉（變成灰色的「僅 DNS」）**。如果維持橘色雲朵，你的連線會被 Cloudflare 擋住，完全連不進去！
   - 儲存紀錄。

2. **獲取 API Token (權杖)**：
   - 點擊 Cloudflare 畫面右上角你的頭像，選擇 **「我的個人檔案」**。
   - 左側選單點擊 **「API 權杖 (API Tokens)」**，然後點擊 **「建立權杖」**。
   - 找到 **「編輯區域 DNS (Edit zone DNS)」** 這個範本，點擊「使用範本」。
   - **區域資源 (Zone Resources)** 設定如下：
     - `包含 (Include)` -> `特定區域 (Specific zone)` -> `[選擇你的網域]`
   - 點擊「繼續以摘要」並建立。
   - > [!IMPORTANT]
     > 畫面上會出現一長串密碼（Token），**請立刻把它複製並存到記事本**。這個密碼只會顯示這一次！

---

## 🟢 Step 3: 架設大門守衛 (Nginx Proxy Manager)
我們要在伺服器上跑一個帶有網頁介面的 Nginx，這叫 Nginx Proxy Manager (NPM)，它能幫我們自動申請憑證。

1. 在伺服器上找一個空資料夾（例如 `C:\npm` 或 Linux 的 `~/npm`），建立一個 `docker-compose.yml` 檔案，內容如下：
   ```yaml
   version: '3.8'
   services:
     app:
       image: 'jc21/nginx-proxy-manager:latest'
       restart: unless-stopped
       ports:
         - '80:80'
         - '81:81'
         - '443:443'
       volumes:
         - ./data:/data
         - ./letsencrypt:/etc/letsencrypt
   ```
2. 開啟終端機，在該目錄下執行啟動指令：
   ```bash
   docker-compose up -d
   ```
3. 打開瀏覽器，輸入 `http://localhost:81` 進入 NPM 的管理後台。
   *(預設帳號：`admin@example.com` / 密碼：`changeme`)*

---

## 🟢 Step 4: 申請 HTTPS 憑證與設定代理
這是最神奇的一步，我們要用剛剛的 Token 自動拿憑證，並把網域對應到我們的 File Explorer。

1. **申請憑證 (DNS-01 挑戰)**：
   - 在 NPM 後台，點擊上方選單的 **「SSL Certificates」** -> **「Add SSL Certificate」** -> **「Let's Encrypt」**。
   - **Domain Names**：填入你剛剛設定的網址（例如 `files.yourdomain.com`）。
   - **Email Address**：填你的信箱。
   - **Use a DNS Challenge**：✅ **打勾**。
   - **DNS Provider**：下拉選擇 `Cloudflare`。
   - **Credentials File Content**：框框裡面會有一段範例程式碼，把裡面的 `your_cloudflare_api_token` 替換成你 **Step 2 複製的那一長串 Token**。
   - 點擊 **Save**。等待約 30 秒，如果成功，你的憑證就會出現在列表中！

2. **設定反向代理 (Proxy Host)**：
   - 點擊上方選單的 **「Hosts」** -> **「Proxy Hosts」** -> **「Add Proxy Host」**。
   - **[Details 頁籤]**：
     - **Domain Names**：`files.yourdomain.com`
     - **Scheme**：`http`
     - **Forward Hostname / IP**：填入你 File Explorer 的伺服器 IP（如果 NPM 跟 File Explorer 在同一台電腦上，填伺服器的區域網路 IP，例如 `192.168.1.100` 或 Docker Gateway IP，**不要填 `localhost` 或 `127.0.0.1`**，因為在 Docker 裡 localhost 指的是容器自己）。
     - **Forward Port**：填入 File Explorer 的埠號（例如 `8000`）。
     - 打勾 `Block Common Exploits` 與 `Websockets Support`。
   - **[SSL 頁籤]**：
     - SSL Certificate 下拉選擇你剛剛申請好的憑證。
     - 打勾 `Force SSL` 與 `HTTP/2 Support`。
   - **[Advanced 頁籤] (為了大檔案上傳優化)**：
     - 在框框裡貼上以下 Nginx 設定，解決大檔案中斷問題：
     ```nginx
     client_max_body_size 0; # 無限制上傳大小
     proxy_read_timeout 3600s;
     proxy_send_timeout 3600s;
     proxy_request_buffering off;
     ```
   - 點擊 **Save**。

---

## 🟢 Step 5: 測試與收尾
現在，確認你的筆電或手機**有打開 Tailscale**，在瀏覽器輸入 `https://files.yourdomain.com`，你應該就能看到閃亮的綠色鎖頭，並且直接進入你的 File Explorer 了！

> [!TIP]
> **下一步我們該做什麼？**
> 這份指南裡的 Step 1 ~ Step 4 是你可以自己先動手設定的環境基礎。
> 
> 等你把網域和 Nginx Proxy Manager 搞定後，你會需要把我們這套 File Explorer **打包成正式版的 Docker 容器**（目前我們還是用 `npm run dev` 在開發模式跑）。
> **到時候我可以幫你寫專案專屬的 `Dockerfile` 和啟動腳本！**
