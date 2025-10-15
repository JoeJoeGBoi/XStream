import os
import time
import subprocess
from googleapiclient.discovery import build
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
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def get_drive_videos():
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType contains 'video/'",
        pageSize=1000, fields="files(id, name)").execute()
    return results.get('files', [])

def build_output_urls():
    outputs = [LOCAL_RTMP_URL]
    if YOUTUBE_URL:
        outputs.append(YOUTUBE_URL)
    if TWITCH_URL:
        outputs.append(TWITCH_URL)
    tee_output = "|".join(outputs)
    return f"[f=flv]{tee_output}"

def stream_videos(files):
    for f in files:
        file_id = f['id']
        name = f['name']
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        print(f"\n🎬 Streaming: {name}")

        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', url,
            '-c:v', 'libx264', '-preset', 'veryfast',
            '-c:a', 'aac', '-ar', '44100', '-b:a', '128k',
            '-f', 'tee', build_output_urls()
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=False)
        except Exception as e:
            print(f"⚠️ Error streaming {name}: {e}")
            continue

def main():
    print("🚀 Drive Auto-Stream Multi-Platform RTMP Server Started.")
    while True:
        files = get_drive_videos()
        if not files:
            print("❌ No videos found. Retrying...")
            time.sleep(REFRESH_INTERVAL)
            continue

        print(f"✅ Found {len(files)} videos. Beginning broadcast...")
        stream_videos(files)
        print(f"🔁 Playlist done. Rechecking in {REFRESH_INTERVAL//60} minutes.")
        time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    main()