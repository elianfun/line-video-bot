import os
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, Configuration, MessagingApiBlob, MessagingApi, ReplyMessageRequest, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, VideoMessageContent
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

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

handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)


def get_drive_service():
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

    return build("drive", "v3", credentials=creds)


def upload_to_drive(file_path: Path):
    try:
        service = get_drive_service()
        file_metadata = {
            "name": file_path.name,
            "parents": [GOOGLE_DRIVE_FOLDER_ID],
        }
        media = MediaFileUpload(str(file_path), mimetype="video/mp4", resumable=True)
        uploaded = service.files().create(
            body=file_metadata, media_body=media, fields="id, name"
        ).execute()
        print(f"[Drive] 已上傳：{uploaded['name']} (id={uploaded['id']})")
    except Exception as e:
        print(f"[Drive] 上傳失敗：{e}")


def download_and_save(message_id: str, chat_id: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"video_{timestamp}_{message_id}.mp4"
    file_path = DOWNLOAD_DIR / filename

    with ApiClient(line_config) as api_client:
        blob_api = MessagingApiBlob(api_client)
        content = blob_api.get_message_content(message_id)

    with open(file_path, "wb") as f:
        f.write(content)

    print(f"[本地] 已儲存：{file_path}")
    push_text(chat_id, f"📁 已存檔：{filename}")

    if UPLOAD_DRIVE and GOOGLE_DRIVE_FOLDER_ID:
        upload_to_drive(file_path)
        push_text(chat_id, "☁️ 已上傳至 Google 雲端硬碟")
        if not SAVE_LOCAL:
            file_path.unlink()
            print(f"[本地] 已刪除暫存：{file_path.name}")


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


def reply_text(reply_token: str, text: str):
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def push_text(to: str, text: str):
    with ApiClient(line_config) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(
                to=to,
                messages=[TextMessage(text=text)],
            )
        )


@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video(event):
    message_id = event.message.id
    reply_token = event.reply_token
    print(f"[LINE] 收到影片訊息 id={message_id}")

    chat_id = event.source.group_id if hasattr(event.source, "group_id") else event.source.user_id
    reply_text(reply_token, "✅ 已收到影片，存檔中...")

    t = threading.Thread(target=download_and_save, args=(message_id, chat_id), daemon=True)
    t.start()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
