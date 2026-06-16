# LINE 群組影片自動備份 Bot

接收 LINE 群組中的影片，自動下載並上傳至 Google 雲端硬碟。

---

## 目錄

- [事前準備（兩平台通用）](#事前準備兩平台通用)
- [Windows 安裝教學](#windows-安裝教學)
- [Ubuntu Linux 安裝教學](#ubuntu-linux-安裝教學)
- [設定 .env](#設定-env)
- [首次授權 Google Drive](#首次授權-google-drive)
- [使用 ngrok 對外開放](#使用-ngrok-對外開放)
- [設定 LINE Webhook](#設定-line-webhook)
- [常見問題](#常見問題)

---

## 事前準備（兩平台通用）

以下帳號和檔案需要在搬移前準備好：

1. **LINE Developers 帳號**，並取得：
   - `Channel Secret`
   - `Channel Access Token`

2. **Google Cloud 專案**，並取得：
   - `oauth_credentials.json`（OAuth 2.0 桌面應用程式金鑰）
   - 已建立好的 Google Drive 資料夾，並記下其 **資料夾 ID**（URL 最後一段）

3. **複製整個專案資料夾**到新機器（包含 `oauth_credentials.json`、`token.json`）

> ⚠️ `token.json` 若一起複製過去，可免去重新 Google 授權的步驟。若沒複製，首次執行時會自動跳出瀏覽器要求重新授權。

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

### 2. 複製專案到新機器

將整個 `line-video-bot` 資料夾複製到新電腦，例如放在：

```
C:\Users\你的名字\line-video-bot\
```

### 3. 建立虛擬環境並安裝套件

開啟命令提示字元（cmd），進入專案資料夾：

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

### 1. 更新系統並安裝 Python

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv -y
python3 --version
```

### 2. 複製專案到伺服器

**方法 A：從你的電腦上傳（用 scp）**

在你的 Windows 本機執行：

```powershell
scp -r C:\Users\你的名字\line-video-bot 使用者@伺服器IP:~/line-video-bot
```

**方法 B：手動建立資料夾後上傳**

```bash
mkdir ~/line-video-bot
```

再用 SFTP 或其他工具上傳檔案。

### 3. 建立虛擬環境並安裝套件

```bash
cd ~/line-video-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 設定 .env

參考下方 [設定 .env](#設定-env) 章節。

```bash
nano .env
```

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
- 停止：先找到 PID 再 kill

```bash
ps aux | grep app.py   # 找到 PID
kill PID               # 停止
```

ngrok 也可以同樣方式背景執行：

```bash
nohup ngrok http 5000 > ngrok.log 2>&1 &
```

查看 ngrok 對外網址：

```bash
cat ngrok.log
# 或用 API 查詢
curl http://localhost:4040/api/tunnels
```

---

#### 方法 B：screen（可隨時回來查看 log）

先安裝：

```bash
sudo apt install screen -y
```

啟動一個命名 session：

```bash
screen -S linebot
source venv/bin/activate
python app.py
```

按 `Ctrl + A`，再按 `D` 離開（bot 繼續跑）。

之後要回來查看：

```bash
screen -r linebot
```

ngrok 也可以開一個獨立 session：

```bash
screen -S ngrok
ngrok http 5000
```

按 `Ctrl + A`，再按 `D` 離開。

---

#### 方法 C：systemd（推薦，開機自動啟動、自動重啟）

建立 service 設定檔：

```bash
sudo nano /etc/systemd/system/line-video-bot.service
```

貼入以下內容（記得修改路徑和使用者名稱）：

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

啟用並啟動服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable line-video-bot
sudo systemctl start line-video-bot
```

查看執行狀態：

```bash
sudo systemctl status line-video-bot
```

查看即時 log：

```bash
journalctl -u line-video-bot -f
```

若要同時用 systemd 管理 ngrok，建立第二個 service：

```bash
sudo nano /etc/systemd/system/ngrok.service
```

貼入以下內容：

```ini
[Unit]
Description=ngrok tunnel
After=network.target

[Service]
User=你的使用者名稱
ExecStart=/usr/bin/ngrok http 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

啟用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok
```

查看 ngrok 對外網址：

```bash
curl http://localhost:4040/api/tunnels
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
```

| 變數 | 說明 |
|------|------|
| `LINE_CHANNEL_SECRET` | LINE Developers 後台取得 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers 後台取得 |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive 資料夾網址最後一段 |
| `SAVE_LOCAL` | `true` = 同時保留本機備份 |
| `UPLOAD_DRIVE` | `true` = 啟用上傳 Google Drive |

---

## 首次授權 Google Drive

若沒有一起複製 `token.json`，首次執行時會自動開啟瀏覽器進行 Google 授權：

1. 瀏覽器彈出 Google 登入頁面
2. 選擇有 Drive 權限的 Google 帳號
3. 授權完成後，`token.json` 會自動產生，之後不需要再授權

> ⚠️ Ubuntu 無頭伺服器（無桌面環境）無法直接開瀏覽器。建議先在有桌面的機器執行一次產生 `token.json`，再把 `token.json` 複製到伺服器。

---

## 使用 ngrok 對外開放

LINE Webhook 需要 HTTPS 公開網址。若沒有固定 IP 或域名，可用 ngrok。

### 安裝 ngrok

**Windows：**

前往 [https://ngrok.com/download](https://ngrok.com/download) 下載，解壓縮後執行：

```cmd
ngrok http 5000
```

**Ubuntu：**

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### 註冊 ngrok 並設定 authtoken

ngrok 需要免費帳號才能使用。

1. 前往 [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup) 註冊
2. 登入後到 [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) 複製你的 token
3. 執行以下指令設定（只需設定一次）：

```bash
ngrok config add-authtoken 你的token
```

### 啟動 ngrok

**注意：啟動前請確認 `app.py` 已經在另一個 terminal 跑起來了。**

```bash
ngrok http 5000
```

啟動後會看到類似：

```
Forwarding  https://xxxx-xxx-xxx.ngrok-free.app -> http://localhost:5000
```

複製 `https://` 開頭的網址，填入 LINE Webhook。

### ngrok 常見錯誤

**ERR_NGROK_334 - endpoint already online**

表示舊的 ngrok session 還掛在伺服器上，解法：

1. 先終止本機殘留進程：`pkill ngrok`
2. 前往 [https://dashboard.ngrok.com/endpoints](https://dashboard.ngrok.com/endpoints)
3. 找到舊的 endpoint，點右側 `...` → **Stop Endpoint**
4. 再重新執行 `ngrok http 5000`

---

## 設定 LINE Webhook

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Messaging API Channel
3. 進入 **Messaging API** 頁籤
4. 在 **Webhook URL** 填入：

   ```
   https://你的ngrok網址/callback
   ```

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
