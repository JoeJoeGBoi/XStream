# XStream – Google Drive Auto Streamer

XStream reads video files from a Google Drive folder and restreams them to an RTMP server. By default it publishes to a local nginx-rtmp instance and can optionally relay the feed to external platforms such as YouTube or Twitch.

## Features
- Cycles through every video in the configured Google Drive folder.
- Restreams to a local RTMP endpoint plus optional downstream platforms via FFmpeg tee output.
- Docker image with nginx-rtmp pre-configured to accept the local stream.
- Friendly error handling for missing credentials or misconfigured environments.

## Requirements
- Google Cloud project with the **Google Drive API** enabled and a service account that has access to the target Drive folder.
- Service account credentials JSON file (downloaded from Google Cloud Console).
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on the system PATH when running locally.
- Python 3.9+ (for local runs) or Docker Desktop (for containerised runs).

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `FOLDER_ID` | ✅ | Google Drive folder ID containing the videos to play. |
| `SERVICE_ACCOUNT_FILE` | ✅ | Absolute path to the service account credentials JSON file. Defaults to `/app/credentials.json` inside the container. |
| `RTMP_STREAM_KEY` | ➖ | Suffix for the local RTMP URL. Defaults to `stream`, resulting in `rtmp://localhost/live/stream`. |
| `YOUTUBE_URL` | ➖ | Optional RTMP endpoint for YouTube, e.g. `rtmp://a.rtmp.youtube.com/live2/KEY`. |
| `TWITCH_URL` | ➖ | Optional RTMP endpoint for Twitch, e.g. `rtmp://live.twitch.tv/app/STREAM_KEY`. |
| `REFRESH_INTERVAL` | ➖ | Seconds to wait before checking Drive again. Defaults to `600` (10 minutes). |

## Running on Windows 10 with PowerShell
1. **Install prerequisites**
   - [Python 3.10+](https://www.python.org/downloads/windows/)
   - [FFmpeg](https://ffmpeg.org/download.html) – easiest via [Chocolatey](https://chocolatey.org/install) or [winget](https://learn.microsoft.com/windows/package-manager/winget/):
     ```powershell
     winget install --id=Gyan.FFmpeg.Full --source=winget
     ```
2. **Clone the repository**
   ```powershell
   git clone https://github.com/your-org/XStream.git
   cd XStream
   ```
3. **Create and activate a virtual environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. **Install Python dependencies**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. **Provide Google credentials**
   - Download your service account JSON file to a secure location, e.g. `C:\secrets\credentials.json`.
6. **Configure environment variables for the session**
   ```powershell
   $env:FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID"
   $env:SERVICE_ACCOUNT_FILE = "C:\secrets\credentials.json"
   # Optional destinations
   $env:YOUTUBE_URL = "rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY"
   $env:TWITCH_URL = "rtmp://live.twitch.tv/app/YOUR_STREAM_KEY"
   ```
7. **Run the streamer**
   ```powershell
   python drive_autostream.py
   ```
8. **Verify the RTMP endpoint**
   - Open VLC or OBS and connect to `rtmp://localhost/live/stream` (or your custom stream key).
   - Alternatively check the nginx status endpoint at <http://localhost:8080> for `RTMP Server Running`.

## Running with Docker Desktop
1. **Ensure Docker Desktop is running** on Windows or macOS.
2. **Build the image**
   ```powershell
   docker build -t xstream .
   ```
3. **Run the container** (mount your credentials read-only and expose the RTMP ports):
   ```powershell
   docker run --rm -it \
     -p 1935:1935 -p 8080:8080 \
     -e FOLDER_ID="YOUR_GOOGLE_DRIVE_FOLDER_ID" \
     -e SERVICE_ACCOUNT_FILE="/app/credentials.json" \
     -e YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY" \
     -v C:\secrets\credentials.json:/app/credentials.json:ro \
     xstream
   ```
   Replace optional environment variables with your own values or omit them if you only need the local RTMP relay.
4. **Test the stream**
   - Point VLC/OBS at `rtmp://localhost/live/stream`.
   - Visit <http://localhost:8080> to confirm nginx-rtmp is running.
5. **Stopping** – press `Ctrl+C` in the terminal or run `docker stop <container-id>`.

## Development Tips
- The script logs progress to stdout; when running in Docker you can view logs with `docker logs <container-id>`.
- Update `REFRESH_INTERVAL` if you need faster or slower polling of Google Drive.
- Videos are streamed sequentially. Update `stream_videos` if you need shuffling or filtering logic.

## Troubleshooting
- **`Unable to initialise Google Drive service`**: Check that `FOLDER_ID` is set and that the credentials JSON path is valid.
- **`Failed to retrieve Drive files`**: The service account may not have access to the folder; share the folder with the service account email.
- **FFmpeg exit codes**: Inspect the log output for codec or network errors. Ensure the downstream RTMP URLs are reachable and credentials are valid.

## License
This project is released under the MIT License.
