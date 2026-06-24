import asyncio
import json
import os
import queue
import subprocess
import threading
import time
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
UPLOAD_DRIVE = os.environ.get("UPLOAD_DRIVE", "false").lower() == "true"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
SILENT_MODE = os.environ.get("SILENT_MODE", "false").lower() == "true"
ENABLE_VIDEO = os.environ.get("ENABLE_VIDEO", "true").lower() == "true"
ENABLE_IMAGE = os.environ.get("ENABLE_IMAGE", "true").lower() == "true"

handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

# 排隊處理，避免同時下載多個檔案觸發 LINE API 限制
_media_queue = queue.Queue()

def _queue_worker():
    while True:
        message_id, chat_id, media_type = _media_queue.get()
        try:
            download_and_save(message_id, chat_id, media_type)
        finally:
            _media_queue.task_done()

threading.Thread(target=_queue_worker, daemon=True).start()

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


def get_video_dimensions(file_path: Path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(file_path)],
        capture_output=True, text=True
    )
    streams = json.loads(result.stdout).get("streams", [])
    for s in streams:
        if s.get("codec_type") == "video":
            return s.get("width", 0), s.get("height", 0)
    return 0, 0


def post_to_telegram(file_path: Path, mimetype: str, caption: str):
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(read_timeout=300, write_timeout=300, connect_timeout=30)
    bot = Bot(token=TELEGRAM_BOT_TOKEN, base_url="http://localhost:8081/bot", request=request)

    async def _send():
        with open(file_path, "rb") as f:
            if mimetype.startswith("video"):
                width, height = get_video_dimensions(file_path)
                await bot.send_video(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    video=f,
                    caption=caption,
                    width=width or None,
                    height=height or None,
                )
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

        caption = f"📅 {timestamp_caption}"
        tasks_needed = 0
        tasks_ok = 0

        if UPLOAD_DRIVE and GOOGLE_DRIVE_FOLDER_ID:
            tasks_needed += 1
            try:
                upload_to_drive(file_path, mimetype=mimetype)
                tasks_ok += 1
                if not SILENT_MODE:
                    push_text(chat_id, "☁️ 已上傳至 Google 雲端硬碟")
            except Exception as e:
                print(f"[Drive] 上傳失敗：{e}")
                push_text(chat_id, "❌ Google Drive 上傳失敗，本地檔案保留。")

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            tasks_needed += 1
            try:
                post_to_telegram(file_path, mimetype, caption)
                tasks_ok += 1
                if not SILENT_MODE:
                    push_text(chat_id, "📢 已發布到 Telegram Channel")
            except Exception as e:
                print(f"[Telegram] 發布失敗：{e}")
                push_text(chat_id, "❌ Telegram 發布失敗，本地檔案保留。")
            finally:
                time.sleep(10)

        if tasks_needed > 0 and tasks_ok == tasks_needed:
            file_path.unlink()
            print(f"[本地] 已刪除：{file_path.name}")
        elif tasks_needed > 0:
            print(f"[本地] 保留：{file_path.name}（有操作失敗）")

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
    if not ENABLE_VIDEO:
        return
    message_id = event.message.id
    print(f"[LINE] 收到影片訊息 id={message_id}")
    chat_id = get_chat_id(event)
    if not SILENT_MODE:
        reply_text(event.reply_token, "✅ 已收到影片，存檔中...")
    _media_queue.put((message_id, chat_id, "video"))


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    if not ENABLE_IMAGE:
        return
    message_id = event.message.id
    print(f"[LINE] 收到圖片訊息 id={message_id}")
    chat_id = get_chat_id(event)
    if not SILENT_MODE:
        reply_text(event.reply_token, "✅ 已收到圖片，存檔中...")
    _media_queue.put((message_id, chat_id, "image"))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
