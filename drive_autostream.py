"""Google Drive to multi-platform RTMP restreamer."""
import os
import sys
import time
import subprocess
from typing import List, Dict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# ==== ENV CONFIG ====
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', '/app/credentials.json')
FOLDER_ID = os.getenv('FOLDER_ID')
LOCAL_RTMP_URL = f"rtmp://localhost/live/{os.getenv('RTMP_STREAM_KEY', 'stream')}"
YOUTUBE_URL = os.getenv('YOUTUBE_URL', '')
TWITCH_URL = os.getenv('TWITCH_URL', '')
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '600'))

# ==== AUTH ====
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def load_drive_service():
    """Create an authenticated Google Drive service client."""
    if not FOLDER_ID:
        raise ValueError('FOLDER_ID environment variable is required.')

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Service account file not found at '{SERVICE_ACCOUNT_FILE}'. "
            'Set SERVICE_ACCOUNT_FILE to the credentials JSON file.'
        )

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)


def get_drive_videos(drive_service) -> List[Dict[str, str]]:
    try:
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType contains 'video/'",
            pageSize=1000,
            fields="files(id, name)",
        ).execute()
    except HttpError as exc:
        print(f"⚠️ Failed to retrieve Drive files: {exc}")
        return []

    return results.get('files', [])


def build_output_urls() -> str:
    outputs = [LOCAL_RTMP_URL]
    if YOUTUBE_URL:
        outputs.append(YOUTUBE_URL)
    if TWITCH_URL:
        outputs.append(TWITCH_URL)
    tee_output = "|".join(outputs)
    return f"[f=flv]{tee_output}"


def stream_videos(files: List[Dict[str, str]]):
    for file_info in files:
        file_id = file_info['id']
        name = file_info['name']
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        print(f"\n🎬 Streaming: {name}")

        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', url,
            '-c:v', 'libx264', '-preset', 'veryfast',
            '-c:a', 'aac', '-ar', '44100', '-b:a', '128k',
            '-f', 'tee', build_output_urls(),
        ]

        try:
            result = subprocess.run(ffmpeg_cmd, check=False)
            if result.returncode != 0:
                print(f"⚠️ FFmpeg exited with code {result.returncode} while streaming {name}.")
        except Exception as exc:
            print(f"⚠️ Error streaming {name}: {exc}")
            continue


def main():
    try:
        drive_service = load_drive_service()
    except Exception as exc:  # noqa: BLE001 - show friendly error and exit
        print(f"❌ Unable to initialise Google Drive service: {exc}")
        sys.exit(1)

    print("🚀 Drive Auto-Stream Multi-Platform RTMP Server Started.")
    while True:
        files = get_drive_videos(drive_service)
        if not files:
            print("❌ No videos found. Retrying...")
            time.sleep(REFRESH_INTERVAL)
            continue

        print(f"✅ Found {len(files)} videos. Beginning broadcast...")
        stream_videos(files)
        print(f"🔁 Playlist done. Rechecking in {REFRESH_INTERVAL // 60} minutes.")
        time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
