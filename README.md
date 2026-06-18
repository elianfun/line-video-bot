# LINE 群組影片自動備份 Bot

接收 LINE 群組中的影片與圖片，自動下載並備份至本機、上傳 Google 雲端硬碟，同時轉發到 Telegram Channel。

---

## 目錄

- [功能總覽](#功能總覽)
- [申請 LINE Bot](#申請-line-bot)
- [申請 Google Cloud 與 Drive 權限](#申請-google-cloud-與-drive-權限)
- [申請 Telegram Bot](#申請-telegram-bot)
- [申請 Telegram API ID 與 Hash](#申請-telegram-api-id-與-hash)
- [Linux 伺服器遷移](#linux-伺服器遷移)
- [Windows 安裝教學](#windows-安裝教學)
- [Ubuntu Linux 安裝教學](#ubuntu-linux-安裝教學)
- [設定 .env](#設定-env)
- [設定 Telegram Channel](#設定-telegram-channel)
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

## 申請 LINE Bot

### 1. 建立 LINE Developers 帳號

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 用 LINE 帳號登入
3. 同意開發者條款

### 2. 建立 Provider

1. 登入後點 **Create a new provider**
2. 輸入 Provider 名稱（例如你的名字或組織名稱）
3. 點 **Create**

### 3. 建立 Messaging API Channel

1. 在 Provider 頁面點 **Create a new channel**
2. 選擇 **Messaging API**
3. 填入以下資訊：
   - **Channel name**：Bot 的名稱（會顯示在 LINE 上）
   - **Channel description**：簡短說明
   - **Category / Subcategory**：隨意選擇
4. 勾選同意條款，點 **Create**

### 4. 取得 Channel Secret

1. 進入剛建立的 Channel
2. 點 **Basic settings** 頁籤
3. 找到 **Channel secret**，點旁邊的複製按鈕
4. 記下這串字，填入 `.env` 的 `LINE_CHANNEL_SECRET`

### 5. 取得 Channel Access Token

1. 點 **Messaging API** 頁籤
2. 滾到最下方找到 **Channel access token**
3. 點 **Issue** 產生 Token
4. 複製這串 Token，填入 `.env` 的 `LINE_CHANNEL_ACCESS_TOKEN`

### 6. 將 Bot 加入群組

1. 在 **Messaging API** 頁籤找到 **Bot basic ID**（格式為 `@xxx`）
2. 在 LINE 群組中加入這個 Bot
3. 到 [LINE Official Account Manager](https://manager.line.biz/) → **設定** → **回應設定**
   - 將「加入群組的回應」設為**開啟**
   - 將「Webhook」設為**開啟**

---

## 申請 Google Cloud 與 Drive 權限

### 1. 建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點上方專案選單 → **新增專案**
3. 輸入專案名稱（例如 `line-video-bot`），點 **建立**

### 2. 啟用 Google Drive API

1. 進入剛建立的專案
2. 左側選單點 **API 和服務** → **程式庫**
3. 搜尋 **Google Drive API**，點進去後點 **啟用**

### 3. 建立 OAuth 2.0 憑證

1. 左側選單點 **API 和服務** → **憑證**
2. 點上方 **+ 建立憑證** → **OAuth 用戶端 ID**
3. 若出現「設定同意畫面」提示，先點進去設定：
   - User Type 選 **外部**，點 **建立**
   - 填入 App name（隨意）、User support email（你的信箱）
   - 滾到最下方填 Developer contact email，點 **儲存並繼續**
   - **範圍** 頁面直接點 **儲存並繼續**
   - **測試使用者** 頁面點 **+ ADD USERS**，加入你的 Google 帳號，點 **儲存並繼續**
4. 回到憑證頁面，再次點 **+ 建立憑證** → **OAuth 用戶端 ID**
5. 應用程式類型選 **桌面應用程式**
6. 名稱隨意填，點 **建立**
7. 點 **下載 JSON**，將下載的檔案改名為 `oauth_credentials.json`
8. 將 `oauth_credentials.json` 放到專案根目錄（`line-video-bot/` 資料夾內）

### 4. 建立 Google Drive 資料夾並取得 ID

1. 前往 [Google Drive](https://drive.google.com/)
2. 新增一個資料夾（例如 `LINE備份`）
3. 點進這個資料夾，複製網址列最後一段字串，即為 **資料夾 ID**

```
https://drive.google.com/drive/folders/1ABCdefGHIjklMNO  ← 這段
```

4. 填入 `.env` 的 `GOOGLE_DRIVE_FOLDER_ID`

---

## 申請 Telegram Bot

### 1. 建立 Bot

1. 打開 Telegram，搜尋 **`@BotFather`**（有藍色勾勾才是官方）
2. 點 **Start**，輸入：
   ```
   /newbot
   ```
3. 輸入 Bot 的**顯示名稱**（例如 `影片備份Bot`）
4. 輸入 Bot 的 **username**（必須以 `bot` 結尾，例如 `myvideobackup_bot`）
5. 成功後取得 Token，格式如下：
   ```
   123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```
6. 填入 `.env` 的 `TELEGRAM_BOT_TOKEN`

### 2. 建立 Telegram Channel

1. Telegram 點左上角鉛筆圖示 → **New Channel**
2. 填入頻道名稱（例如 `影片備份`）
3. 類型選 **Private**（私人，之後可改為公開）
4. 成員可先跳過，直接建立

### 3. 將 Bot 加入 Channel 並設為管理員

1. 進入 Channel → 點頻道名稱 → **Administrators**
2. 點 **Add Administrator**，搜尋你的 Bot username
3. 確認 **Post Messages** 有勾選，點 **Save**

### 4. 取得 Channel ID

**私人 Channel：**
1. 在 Channel 中隨意傳一則訊息
2. 將這則訊息**轉發**給 `@userinfobot`
3. userinfobot 回傳類似：`Forwarded from chat #-1001234567890`
4. 記下這串數字（含負號），填入 `.env` 的 `TELEGRAM_CHANNEL_ID`

**公開 Channel：**
直接用 `@頻道username` 填入即可。

> ✅ 私人 Channel 隨時可轉為公開：Channel 設定 → **Channel Type** → Public。Channel ID 不變，`.env` 不需要修改。

---

## 申請 Telegram API ID 與 Hash

> 此步驟只有在使用**自架 Telegram Bot API Server**（突破 50MB 限制）時才需要。

1. 前往 [https://my.telegram.org/](https://my.telegram.org/)
2. 輸入你的 Telegram 手機號碼（含國碼，例如 `+886912345678`）
3. Telegram 會發送驗證碼，輸入後登入
4. 點 **API development tools**
5. 填入：
   - **App title**：隨意（例如 `linebot`）
   - **Short name**：隨意（例如 `linebot`，5-32 字元英數字）
   - 其他欄位留空
6. 點 **Create application**
7. 取得 **`App api_id`**（數字）和 **`App api_hash`**（英數字串）
8. 這兩個值在後面的 Docker 指令中使用

---

## Linux 伺服器遷移

當需要搬移到另一台 Linux 時，只需備份三個檔案，其餘從 GitHub 重新安裝即可。

### 1. 在舊機器備份以下三個檔案

| 檔案 | 說明 |
|------|------|
| `.env` | 所有 Token 和設定 |
| `oauth_credentials.json` | Google Cloud OAuth 憑證 |
| `token.json` | Google 授權快取，沒有需重新跑瀏覽器授權 |

從舊機器複製到本機（在 Windows 執行）：

```powershell
scp 使用者@舊伺服器IP:~/line-video-bot/.env .
scp 使用者@舊伺服器IP:~/line-video-bot/oauth_credentials.json .
scp 使用者@舊伺服器IP:~/line-video-bot/token.json .
```

### 2. 在新機器安裝環境

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git ffmpeg docker.io -y
sudo systemctl enable docker
sudo systemctl start docker
```

### 3. Clone 專案

```bash
git clone https://github.com/elianfun/line-video-bot.git
cd line-video-bot
```

### 4. 上傳備份檔案到新機器

從 Windows 本機執行：

```powershell
scp .env 使用者@新伺服器IP:~/line-video-bot/
scp oauth_credentials.json 使用者@新伺服器IP:~/line-video-bot/
scp token.json 使用者@新伺服器IP:~/line-video-bot/
```

### 5. 建立虛擬環境並安裝套件

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. 啟動 Telegram Bot API Server

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

### 7. 啟動 Bot

```bash
nohup python app.py > bot.log 2>&1 &
nohup ngrok http 5000 > ngrok.log 2>&1 &
```

### 8. 更新 LINE Webhook

取得新的 ngrok 網址：

```bash
curl http://localhost:4040/api/tunnels
```

到 [LINE Developers Console](https://developers.line.biz/) 更新 Webhook URL 為新網址。

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
| `LINE_CHANNEL_SECRET` | 必填 | LINE Developers → Basic settings → Channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | 必填 | LINE Developers → Messaging API → Channel access token |
| `GOOGLE_DRIVE_FOLDER_ID` | 選填 | Drive 資料夾網址最後一段 |
| `SAVE_LOCAL` | `true` | 保留本機備份於 `downloads/` |
| `UPLOAD_DRIVE` | `false` | 啟用上傳 Google Drive |
| `SILENT_MODE` | `false` | 靜默模式，不發送 LINE 通知（錯誤仍會通知） |
| `ENABLE_VIDEO` | `true` | 是否接收並處理影片 |
| `ENABLE_IMAGE` | `true` | 是否接收並處理圖片 |
| `TELEGRAM_BOT_TOKEN` | 選填 | BotFather 取得，留空則不發布到 Telegram |
| `TELEGRAM_CHANNEL_ID` | 選填 | `@mychannel`（公開）或 `-100xxxxxxxxx`（私人） |

> ⚠️ 修改 `.env` 後必須重新啟動 Bot 才會生效：
> ```bash
> pkill -f "python app.py"
> nohup python app.py > bot.log 2>&1 &
> ```

---

## 設定 Telegram Channel

詳細申請步驟請參考上方 [申請 Telegram Bot](#申請-telegram-bot) 章節。

設定完成後確認：
- Bot 已加入 Channel 並設為管理員
- `.env` 已填入 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHANNEL_ID`
- 重新啟動 Bot

> ⚠️ 標準 Telegram Bot API 單檔上傳限制為 **50MB**。超過請參考下方自架 Server 教學。

---

## 自架 Telegram Bot API Server（突破 50MB 限制）

標準 Bot API 上傳限制為 50MB，自架本機 Server 可支援最大 **2GB**。

### 1. 安裝 Docker

```bash
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 確認已取得 API ID 與 Hash

請先完成 [申請 Telegram API ID 與 Hash](#申請-telegram-api-id-與-hash) 章節。

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

### 4. 確認 Docker 開機自動啟動

```bash
sudo systemctl enable docker
```

---

## 首次授權 Google Drive

若沒有一起複製 `token.json`，首次執行時會自動開啟瀏覽器進行 Google 授權：

1. 瀏覽器彈出 Google 登入頁面
2. 選擇有 Drive 權限的 Google 帳號（與 `oauth_credentials.json` 同一個帳號）
3. 授權完成後，`token.json` 會自動產生，之後不需要再授權

> ⚠️ Ubuntu 無頭伺服器（無桌面環境）無法直接開瀏覽器。建議先在有桌面的機器執行一次 `python app.py` 完成授權，產生 `token.json` 後，再把這個檔案複製到伺服器的專案目錄。

---

## 使用 ngrok 對外開放

LINE Webhook 需要 HTTPS 公開網址。若沒有固定 IP 或域名，可用 ngrok。

### 安裝 ngrok

**Windows：**

前往 [https://ngrok.com/download](https://ngrok.com/download) 下載，解壓縮後執行。

**Ubuntu：**

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### 註冊並設定 authtoken

1. 前往 [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup) 免費註冊
2. 登入後到 [Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) 複製 token
3. 執行（只需一次）：

```bash
ngrok config add-authtoken 你的token
```

### 啟動 ngrok

```bash
ngrok http 5000
```

啟動後複製 `https://` 開頭的網址，填入 LINE Webhook。

### 常見錯誤 ERR_NGROK_334（endpoint already online）

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
4. 在 **Webhook URL** 填入：
   ```
   https://你的ngrok網址/callback
   ```
5. 點擊 **Verify** 確認連線成功（需確保 Bot 已在執行中）
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
建議改用 systemd 管理（見方法 C）。若使用 nohup，重開機後需手動重新執行啟動指令。

**Q: 重開機後 Telegram Bot API Server 沒有啟動？**  
確認 Docker 服務已設定自動啟動：`sudo systemctl enable docker`。Container 本身已設定 `--restart always`，Docker 啟動後會自動重啟。

**Q: Google Cloud 憑證設定同意畫面時出現警告？**  
因為是個人使用的「外部」應用程式，Google 會顯示「未驗證的應用程式」警告。點「繼續」即可，這是正常現象，不影響功能。

**Q: Google Drive Token 每 7 天就失效（invalid_grant）？**  
OAuth 同意畫面的發布狀態若是「測試中」，refresh token 只有 7 天有效期，到期後 Bot 會無法上傳 Drive。解決方法：到 [Google Cloud Console](https://console.cloud.google.com/) → API 和服務 → OAuth 同意畫面 → 點「發布應用程式」改為正式版，之後 refresh token 就不會再自動失效。改完後需重新授權一次（見下方「重新授權 Google Drive」章節）。

**Q: Telegram 全部發布失敗（ConnectError）？**  
app.py 透過 `http://localhost:8081/bot` 連接本機 Telegram Bot API Server，若 Docker Container 未啟動就會連線失敗。確認方式：`sudo docker ps` 看 `telegram-bot-api` 是否在運行。若沒有，執行 `sudo docker start telegram-bot-api` 重新啟動。

**Q: LINE 回覆通知出現 429 Too Many Requests（You have reached your monthly limit）？**  
LINE 免費方案每月只能發送 200 則 push message，Bot 每次處理完影片都會回覆通知給群組，很快就超限。解決方法：在 `.env` 設定 `SILENT_MODE=true`，Bot 就不再發送 LINE 通知（錯誤訊息仍會通知），不會消耗月配額。

**Q: line-bot-sdk 安裝後啟動出現 SyntaxError？**  
`line-bot-sdk==3.14.0` 的自動產生程式碼有語法錯誤，無法啟動。降版至穩定版本即可：
```bash
source venv/bin/activate
pip install "line-bot-sdk==3.13.0"
```

---

## 重新授權 Google Drive

當 `token.json` 失效（出現 `invalid_grant` 錯誤）時，需要重新授權。因伺服器無桌面環境，使用以下流程：

### 1. 刪除舊 token

```bash
rm ~/line-video-bot/token.json
```

### 2. 產生授權網址

```bash
cd ~/line-video-bot
source venv/bin/activate
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'oauth_credentials.json',
    ['https://www.googleapis.com/auth/drive.file'],
    redirect_uri='http://localhost'
)
auth_url, _ = flow.authorization_url(prompt='consent')
print(auth_url)
"
```

### 3. 瀏覽器開啟網址授權

複製印出的網址，用瀏覽器開啟並登入 Google 帳號授權。授權後瀏覽器會跳到 `http://localhost/?code=...` 顯示無法連線，這是正常的，複製網址列中 `code=` 後面的完整字串。

### 4. 用授權碼換取 token

將 `你的授權碼` 替換為上一步複製的內容：

```bash
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
flow = InstalledAppFlow.from_client_secrets_file(
    'oauth_credentials.json',
    ['https://www.googleapis.com/auth/drive.file'],
    redirect_uri='http://localhost'
)
flow.fetch_token(code='你的授權碼')
Path('token.json').write_text(flow.credentials.to_json())
print('授權成功！')
"
```

### 5. 重啟 Bot

```bash
sudo systemctl restart line-video-bot
```

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

### 8. Bot API vs Telegram 客戶端的差異

透過 Bot API 上傳的影片與用手機 App 直接上傳的影片，在 Telegram 的渲染方式不同：客戶端上傳時 Telegram 會自動處理影片元數據，Bot 上傳則需要手動帶入寬高等資訊。兩者使用不同的底層協議（Bot API vs MTProto），這也是為什麼 Bot 上傳有 50MB 限制而客戶端沒有。
