# LINE 群組影片自動備份 Bot

接收 LINE 群組中的影片與圖片，自動下載並備份至本機、上傳 Google 雲端硬碟，同時轉發到 Telegram Channel。

---

## 目錄

- [功能總覽](#功能總覽)
- [事前準備](#事前準備)
- [Windows 安裝教學](#windows-安裝教學)
- [Ubuntu Linux 安裝教學](#ubuntu-linux-安裝教學)
- [設定 .env](#設定-env)
- [設定 Telegram Channel 發布](#設定-telegram-channel-發布)
- [自架 Telegram Bot API Server（突破 50MB 限制）](#自架-telegram-bot-api-server突破-50mb-限制)
- [首次授權 Google Drive](#首次授權-google-drive)
- [使用 ngrok 對外開放](#使用-ngrok-對外開放)
- [設定 LINE Webhook](#設定-line-webhook)
- [常見問題](#常見問題)
- [實作知識點](#實作知識點)

---

## 功能總覽

| 功能 | 說明 |
|------|------|
| 接收影片與圖片 | 支援 LINE 群組或個人訊息 |
| 本機備份 | 儲存至 `downloads/` 資料夾 |
| Google Drive 上傳 | 自動備份到指定資料夾 |
| Telegram Channel 發布 | 自動轉發並附上時間戳記 |
| 排隊處理 | 多個檔案依序處理，避免 API 限速 |
| 靜默模式 | 可關閉 LINE 回覆通知 |
| 影片/圖片開關 | 可分別啟用或停用 |

---

## 事前準備

1. **LINE Developers 帳號**，並取得：
   - `Channel Secret`
   - `Channel Access Token`

2. **Google Cloud 專案**，並取得：
   - `oauth_credentials.json`（OAuth 2.0 桌面應用程式金鑰）
   - 已建立好的 Google Drive 資料夾，記下其 **資料夾 ID**（URL 最後一段）

3. **Telegram Bot**（選填）：
   - 透過 `@BotFather` 建立 Bot，取得 Token
   - 建立 Channel 並將 Bot 設為管理員

> ⚠️ 若要搬移到新機器，請一起複製 `oauth_credentials.json` 和 `token.json`，可免去重新 Google 授權的步驟。

---

## Windows 安裝教學

### 1. 安裝 Python

前往 [https://www.python.org/downloads/](https://www.python.org/downloads/) 下載 Python 3.10 以上版本。

安裝時勾選 **「Add Python to PATH」**，再點 Install Now。

確認安裝成功：

```cmd
python --version
pip --version
```

### 2. 取得專案

將整個 `line-video-bot` 資料夾複製到新電腦，例如放在：

```
C:\Users\你的名字\line-video-bot\
```

### 3. 建立虛擬環境並安裝套件

```cmd
cd C:\Users\你的名字\line-video-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 設定 .env

參考下方 [設定 .env](#設定-env) 章節。

### 5. 啟動 Bot

```cmd
venv\Scripts\activate
python app.py
```

看到以下輸出代表成功：

```
 * Running on http://127.0.0.1:5000
```

### 6. 開機自動啟動（可選）

建立一個 `start_bot.bat` 檔案放在專案資料夾：

```bat
@echo off
cd /d C:\Users\你的名字\line-video-bot
call venv\Scripts\activate
python app.py
```

接著將此捷徑加入「啟動」資料夾：

1. 按 `Win + R`，輸入 `shell:startup`，按 Enter
2. 將 `start_bot.bat` 的捷徑複製到這個資料夾

---

## Ubuntu Linux 安裝教學

### 1. 更新系統並安裝必要套件

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git ffmpeg -y
```

### 2. 取得專案

**方法 A：從 GitHub clone（推薦）**

```bash
git clone https://github.com/elianfun/line-video-bot.git
cd line-video-bot
```

**方法 B：從你的電腦上傳（用 scp）**

在你的 Windows 本機執行：

```powershell
scp -r C:\Users\你的名字\line-video-bot 使用者@伺服器IP:~/line-video-bot
```

**日後更新程式（方法 A 限定）**

```bash
cd ~/line-video-bot
pkill -f "python app.py"
git pull origin main
nohup python app.py > bot.log 2>&1 &
```

### 3. 建立虛擬環境並安裝套件

```bash
cd ~/line-video-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 設定 .env

```bash
nano .env
```

參考下方 [設定 .env](#設定-env) 章節填入資訊。

### 5. 啟動 Bot（前景測試）

```bash
source venv/bin/activate
python app.py
```

### 6. 背景執行 Bot

有三種方式，依需求選擇：

---

#### 方法 A：nohup（最簡單，適合快速測試）

```bash
nohup python app.py > bot.log 2>&1 &
```

- 關掉 terminal 後仍繼續執行
- log 會寫入 `bot.log`
- 查看 log：`tail -f bot.log`
- 停止：`pkill -f "python app.py"`

ngrok 背景執行：

```bash
nohup ngrok http 5000 > ngrok.log 2>&1 &
curl http://localhost:4040/api/tunnels  # 查看對外網址
```

---

#### 方法 B：screen（可隨時回來查看 log）

```bash
sudo apt install screen -y
screen -S linebot
source venv/bin/activate
python app.py
```

按 `Ctrl + A`，再按 `D` 離開（bot 繼續跑）。回來查看：`screen -r linebot`

---

#### 方法 C：systemd（推薦，開機自動啟動、自動重啟）

```bash
sudo nano /etc/systemd/system/line-video-bot.service
```

貼入以下內容（修改路徑和使用者名稱）：

```ini
[Unit]
Description=LINE Video Bot
After=network.target

[Service]
User=你的使用者名稱
WorkingDirectory=/home/你的使用者名稱/line-video-bot
ExecStart=/home/你的使用者名稱/line-video-bot/venv/bin/python app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable line-video-bot
sudo systemctl start line-video-bot
sudo systemctl status line-video-bot  # 查看狀態
journalctl -u line-video-bot -f       # 即時 log
```

---

## 設定 .env

將 `.env.example` 複製一份改名為 `.env`，並填入以下資訊：

```env
LINE_CHANNEL_SECRET=你的_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=你的_Channel_Access_Token
GOOGLE_DRIVE_FOLDER_ID=你的_Google_Drive_資料夾_ID
SAVE_LOCAL=true
UPLOAD_DRIVE=true
SILENT_MODE=false
ENABLE_VIDEO=true
ENABLE_IMAGE=true

# Telegram（選填）
TELEGRAM_BOT_TOKEN=你的_Bot_Token
TELEGRAM_CHANNEL_ID=@你的頻道 或 -100xxxxxxxxx
```

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LINE_CHANNEL_SECRET` | 必填 | LINE Developers 後台取得 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 必填 | LINE Developers 後台取得 |
| `GOOGLE_DRIVE_FOLDER_ID` | 選填 | Drive 資料夾網址最後一段 |
| `SAVE_LOCAL` | `true` | 保留本機備份 |
| `UPLOAD_DRIVE` | `false` | 啟用上傳 Google Drive |
| `SILENT_MODE` | `false` | 靜默模式，不發送 LINE 通知（錯誤除外） |
| `ENABLE_VIDEO` | `true` | 是否處理影片 |
| `ENABLE_IMAGE` | `true` | 是否處理圖片 |
| `TELEGRAM_BOT_TOKEN` | 選填 | BotFather 取得，留空則不發布 |
| `TELEGRAM_CHANNEL_ID` | 選填 | `@mychannel` 或 `-100xxxxxxxxx` |

> ⚠️ 修改 `.env` 後必須重新啟動 Bot 才會生效。

---

## 設定 Telegram Channel 發布

1. 在 Telegram 找 `@BotFather`，輸入 `/newbot` 建立 Bot，取得 `BOT_TOKEN`
2. 建立 Channel（公開或私人皆可）
3. 將 Bot 加入 Channel，設為**管理員**（需有「發布訊息」權限）
4. 取得 Channel ID：
   - 公開 Channel：直接用 `@channel_username`
   - 私人 Channel：將任一訊息轉發給 `@userinfobot`，取得格式為 `-100xxxxxxxxx` 的數字 ID
5. 填入 `.env` 的 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHANNEL_ID`

> ⚠️ 標準 Telegram Bot API 單檔上傳限制為 **50MB**。超過請參考下方自架 Server 教學。

> ✅ 私人 Channel 隨時可以轉為公開，Channel ID 不會改變，`.env` 不需要修改。

---

## 自架 Telegram Bot API Server（突破 50MB 限制）

標準 Bot API 上傳限制為 50MB，自架本機 Server 可支援最大 **2GB**。

### 1. 安裝 Docker

```bash
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 申請 Telegram API 憑證

1. 前往 [https://my.telegram.org/](https://my.telegram.org/) 用手機號碼登入
2. 點 **API development tools**
3. 填入 App title 和 Short name（隨意填，例如 `linebot`）
4. 點 **Create application**，取得 `api_id` 和 `api_hash`

### 3. 啟動本機 Bot API Server

```bash
sudo docker run -d \
  --name telegram-bot-api \
  --restart always \
  -p 8081:8081 \
  -v telegram-bot-api-data:/var/lib/telegram-bot-api \
  -e TELEGRAM_API_ID=你的api_id \
  -e TELEGRAM_API_HASH=你的api_hash \
  aiogram/telegram-bot-api
```

確認有跑起來：

```bash
sudo docker ps
```

看到 `telegram-bot-api` 在 `Up` 狀態即成功。

> ✅ 已設定 `--restart always`，重開機後 Docker 會自動重啟 Server。

### 4. 重啟後確認 Docker 自動啟動

```bash
sudo systemctl enable docker
```

---

## 首次授權 Google Drive

若沒有一起複製 `token.json`，首次執行時會自動開啟瀏覽器進行 Google 授權：

1. 瀏覽器彈出 Google 登入頁面
2. 選擇有 Drive 權限的 Google 帳號
3. 授權完成後，`token.json` 會自動產生，之後不需要再授權

> ⚠️ Ubuntu 無頭伺服器（無桌面環境）無法直接開瀏覽器。建議先在有桌面的機器執行一次產生 `token.json`，再把這個檔案複製到伺服器。

---

## 使用 ngrok 對外開放

LINE Webhook 需要 HTTPS 公開網址。若沒有固定 IP 或域名，可用 ngrok。

**Ubuntu 安裝：**

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
ngrok config add-authtoken 你的token
```

**啟動：**

```bash
ngrok http 5000
```

複製 `https://` 開頭的網址，填入 LINE Webhook。

**常見錯誤 ERR_NGROK_334（endpoint already online）：**

```bash
pkill ngrok
# 再到 https://dashboard.ngrok.com/endpoints 手動 Stop 舊的 endpoint
ngrok http 5000
```

> ⚠️ 免費版 ngrok 每次啟動網址都不同，需重新設定 LINE Webhook。

---

## 設定 LINE Webhook

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Messaging API Channel
3. 進入 **Messaging API** 頁籤
4. 在 **Webhook URL** 填入：`https://你的ngrok網址/callback`
5. 點擊 **Verify** 確認連線成功
6. 開啟 **Use webhook** 開關

---

## 常見問題

**Q: Bot 收到訊息但沒有上傳到 Drive？**  
確認 `.env` 中 `UPLOAD_DRIVE=true` 且 `GOOGLE_DRIVE_FOLDER_ID` 已填入正確 ID，並確認 `token.json` 存在且有效。

**Q: ngrok 每次重啟網址都會變？**  
免費版 ngrok 每次啟動網址都不同，需重新設定 LINE Webhook。若要固定網址，需購買 ngrok 付費方案，或使用有固定 IP 的 VPS 部署。

**Q: Ubuntu 上首次 Google 授權失敗？**  
在有桌面環境的電腦上先執行 `python app.py` 完成授權，產生 `token.json` 後，再把這個檔案複製到 Ubuntu 伺服器的專案目錄。

**Q: 影片只存到本機，沒有上傳？**  
確認 `.env` 的 `UPLOAD_DRIVE=true`（注意大小寫），並重新啟動 Bot。

**Q: Telegram 顯示「發布失敗」？**  
常見原因：Bot 未加入 Channel 或未設為管理員、`TELEGRAM_CHANNEL_ID` 填錯。確認 Bot 是 Channel 管理員且有「發布訊息」權限，ID 格式為 `-100xxxxxxxxx`（私人）或 `@頻道名稱`（公開）。

**Q: 影片超過 50MB 上傳 Telegram 失敗？**  
請參考 [自架 Telegram Bot API Server](#自架-telegram-bot-api-server突破-50mb-限制) 章節，安裝本機 Server 可支援最大 2GB。

**Q: 重開機後 Bot 沒有自動啟動？**  
建議改用 systemd 管理（見 [方法 C](#方法-c：systemd推薦開機自動啟動自動重啟)）。若使用 nohup，重開機後需手動重新執行啟動指令。

**Q: 重開機後 Telegram Bot API Server 沒有啟動？**  
確認 Docker 服務已設定自動啟動：`sudo systemctl enable docker`。Container 本身已設定 `--restart always`，Docker 啟動後會自動重啟。

---

## 實作知識點

### 1. LINE Bot Webhook 運作原理

LINE 伺服器收到群組訊息後，會主動發送 HTTP POST 請求到你設定的 Webhook URL。Bot 收到請求後驗證簽名（`X-Line-Signature`），確認來源合法才處理。這就是為什麼 Bot 需要一個對外可連線的 HTTPS 網址（ngrok 或固定 IP）。

### 2. 為什麼要用背景執行緒（Thread）

LINE 的 Webhook 有回應時間限制，必須在幾秒內回覆 200 OK，否則 LINE 會認為失敗並重試。但下載影片和上傳 Drive 可能需要幾十秒，所以先立即回覆 LINE，再把實際工作丟到背景執行緒處理。

### 3. Queue 排隊機制

同時傳多個影片時，多個執行緒同時呼叫 LINE API 下載內容，容易觸發速率限制導致失敗。改用單一 Worker Thread 搭配 Queue，讓所有檔案依序一個一個處理，避免同時發出太多請求。

### 4. Google Drive Singleton（單例模式）

每次上傳都重新建立 Drive 連線很浪費資源。用 `_drive_service` 全域變數搭配 Double-Checked Locking，確保整個程式生命週期只建立一次連線，且多執行緒同時存取時也安全。

### 5. Telegram Bot API 的 50MB 限制

標準 Telegram Bot API 上傳檔案上限為 50MB，這是官方限制。解法是自架 Telegram Bot API Server（官方開源），讓 Bot 透過本機 Server 與 Telegram 通訊，可支援最大 2GB。本機 Server 跑在 Docker Container，用 `--restart always` 確保重開機後自動啟動。

### 6. ffprobe 偵測影片比例

Bot API 上傳影片時若不帶寬高資訊，Telegram 不知道影片比例，會在播放時加上黑邊。用 `ffprobe` 讀取影片的實際寬高，上傳時帶入 `width` 和 `height` 參數，Telegram 就能正確渲染全螢幕播放。

### 7. 敏感憑證保護

`.env` 存放所有 Token 和 Secret，透過 `.gitignore` 確保不會被 commit 到 GitHub。`oauth_credentials.json` 和 `token.json` 同樣列在 `.gitignore`。公開 repo 上永遠不會有真實憑證。
