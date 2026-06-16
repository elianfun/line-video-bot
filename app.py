import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    MessagingApiBlob,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import ImageMessageContent, MessageEvent, VideoMessageContent
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from telegram import Bot

load_dotenv()

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
SAVE_LOCAL = os.environ.get("SAVE_LOCAL", "true").lower() == "true"
UPLOAD_DRIVE = os.environ.get("UPLOAD_DRIVE", "false").lower() == "true"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SILENT_MODE = os.environ.get("SILENT_MODE", "false").lower() == "true"

handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

_drive_service = None
_drive_lock = threading.Lock()


def get_drive_service():
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    with _drive_lock:
        if _drive_service is not None:
            return _drive_service

        creds = None
        token_path = BASE_DIR / "token.json"
        oauth_path = BASE_DIR / "oauth_credentials.json"

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(oauth_path), SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        _drive_service = build("drive", "v3", credentials=creds)

    return _drive_service


def upload_to_drive(file_path: Path, mimetype: str):
    service = get_drive_service()
    file_metadata = {
        "name": file_path.name,
        "parents": [GOOGLE_DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(str(file_path), mimetype=mimetype, resumable=True)
    uploaded = service.files().create(
        body=file_metadata, media_body=media, fields="id, name"
    ).execute()
    print(f"[Drive] 已上傳：{uploaded['name']} (id={uploaded['id']})")


def post_to_telegram(file_path: Path, mimetype: str, caption: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def _send():
        with open(file_path, "rb") as f:
            if mimetype.startswith("video"):
                await bot.send_video(chat_id=TELEGRAM_CHANNEL_ID, video=f, caption=caption)
            else:
                await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=f, caption=caption)

    asyncio.run(_send())
    print(f"[Telegram] 已發布：{file_path.name}")



def get_chat_id(event) -> str:
    source = event.source
    return getattr(source, "group_id", None) or source.user_id


def push_text(to: str, text: str):
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(to=to, messages=[TextMessage(text=text)])
        )


def reply_text(reply_token: str, text: str):
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def download_and_save(message_id: str, chat_id: str, media_type: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_caption = datetime.now().strftime("%Y-%m-%d %H:%M")

    if media_type == "image":
        filename = f"image_{timestamp}_{message_id}.jpg"
        mimetype = "image/jpeg"
    else:
        filename = f"video_{timestamp}_{message_id}.mp4"
        mimetype = "video/mp4"

    file_path = DOWNLOAD_DIR / filename

    try:
        with ApiClient(line_config) as api_client:
            content = MessagingApiBlob(api_client).get_message_content(message_id)

        file_path.write_bytes(content)
        print(f"[本地] 已儲存：{file_path}")
        if not SILENT_MODE:
            push_text(chat_id, f"📁 已存檔：{filename}")

        if UPLOAD_DRIVE and GOOGLE_DRIVE_FOLDER_ID:
            upload_to_drive(file_path, mimetype=mimetype)
            if not SILENT_MODE:
                push_text(chat_id, "☁️ 已上傳至 Google 雲端硬碟")
            if not SAVE_LOCAL:
                file_path.unlink()
                print(f"[本地] 已刪除暫存：{file_path.name}")

        caption = f"📅 {timestamp_caption}"

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            try:
                post_to_telegram(file_path, mimetype, caption)
                if not SILENT_MODE:
                    push_text(chat_id, "📢 已發布到 Telegram Channel")
            except Exception as e:
                print(f"[Telegram] 發布失敗：{e}")
                push_text(chat_id, "❌ Telegram 發布失敗，請檢查設定。")

    except Exception as e:
        print(f"[錯誤] 處理失敗 (id={message_id})：{e}")
        try:
            push_text(chat_id, "❌ 存檔失敗，請稍後再試。")
        except Exception:
            pass


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video(event):
    message_id = event.message.id
    print(f"[LINE] 收到影片訊息 id={message_id}")
    chat_id = get_chat_id(event)
    if not SILENT_MODE:
        reply_text(event.reply_token, "✅ 已收到影片，存檔中...")
    threading.Thread(
        target=download_and_save, args=(message_id, chat_id, "video"), daemon=True
    ).start()


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    message_id = event.message.id
    print(f"[LINE] 收到圖片訊息 id={message_id}")
    chat_id = get_chat_id(event)
    if not SILENT_MODE:
        reply_text(event.reply_token, "✅ 已收到圖片，存檔中...")
    threading.Thread(
        target=download_and_save, args=(message_id, chat_id, "image"), daemon=True
    ).start()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
