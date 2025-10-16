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

### Step-by-step: gather all required values

1. **Google Drive folder ID (`FOLDER_ID`)**
   1. Open <https://drive.google.com> and navigate to the folder that contains your videos.
   2. Copy the value after `folders/` in the browser address bar. Example: `https://drive.google.com/drive/folders/1AbCdEfGhIj` → folder ID `1AbCdEfGhIj`.
   3. Store this ID—you will paste it into your environment variables or Docker command later.

2. **Service account credentials (`SERVICE_ACCOUNT_FILE`)**
   1. Browse to the [Google Cloud Console](https://console.cloud.google.com/).
   2. Create (or select) a project, then enable the **Google Drive API** via *APIs & Services → Library*.
   3. Go to *APIs & Services → Credentials → Create Credentials → Service account* and follow the prompts.
   4. After the service account is created, open it and grant the **Role → Basic → Viewer** (sufficient for Drive read access).
   5. Within the service account page choose *Keys → Add key → Create new key → JSON*. Download the JSON file to a secure location such as `C:\\secrets\\credentials.json` (Windows) or `/home/user/secrets/credentials.json` (Linux/macOS).
   6. Share the Drive folder from step 1 with the service account email (ends with `iam.gserviceaccount.com`) and give it Viewer access so it can see and download the videos.
   7. Use the absolute path to this JSON file as the `SERVICE_ACCOUNT_FILE` value. When running Docker you will typically mount the file at `/app/credentials.json`.

3. **Optional downstream RTMP URLs (`YOUTUBE_URL`, `TWITCH_URL`)**
   - *YouTube Live*: In YouTube Studio open the **Go Live** dashboard. Copy the *Server URL* and *Stream Key*, then combine them into `rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY`.
   - *Twitch*: Visit <https://stream.twitch.tv/ingests/> to pick a nearby ingest server and pair it with the stream key from the Twitch Creator Dashboard. Combine them into `rtmp://live.twitch.tv/app/YOUR_STREAM_KEY`.
   - Omit these variables if you only need the local nginx-rtmp relay.

4. **Local RTMP stream key (`RTMP_STREAM_KEY`)**
   - Optional suffix for the local nginx-rtmp endpoint. Leaving it blank keeps the default `rtmp://localhost/live/stream`. Set it to another name (e.g. `myshow`) if you prefer a different application path.

5. **Refresh interval (`REFRESH_INTERVAL`)**
   - Controls how long the script waits before polling Google Drive again after finishing the playlist or finding no files. Supply a number of seconds (e.g. `300` for five minutes) if you want something other than the default 600 seconds.

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

### Fixing "error during connect: HEAD http://%2F..."

This message means the Docker CLI cannot reach the Docker daemon. Use the checklist below to recover:

1. **Ensure Docker Desktop is running** – launch it and wait until the status reads *Docker engine running*.
2. **Reset the Docker context** – incorrect contexts leave the CLI pointing at a missing socket.
   - On **Windows PowerShell** run:
     ```powershell
     docker context use default
     Remove-Item Env:DOCKER_HOST -ErrorAction SilentlyContinue
     ```
   - On **macOS/Linux shells** run:
     ```bash
     docker context use default
     unset DOCKER_HOST
     ```
3. **WSL users** – if you rely on the WSL2 backend, open Docker Desktop → *Settings → Resources → WSL Integration* and confirm your distribution is enabled. Then restart Docker Desktop.

After these steps, `docker info` should succeed and `docker build -t xstream .` will work normally.

## Development Tips
- The script logs progress to stdout; when running in Docker you can view logs with `docker logs <container-id>`.
- Update `REFRESH_INTERVAL` if you need faster or slower polling of Google Drive.
- Videos are streamed sequentially. Update `stream_videos` if you need shuffling or filtering logic.

## Installing the Local RTMP Server (nginx-rtmp)

The project ships with an `nginx.conf` tuned for the [nginx-rtmp-module](https://github.com/arut/nginx-rtmp-module). You can
run the ready-made Docker image (see [Running with Docker Desktop](#running-with-docker-desktop)) or install the server
directly on your host machine using the walkthrough below.

### 1. Install nginx with RTMP support

#### Option A – Ubuntu/Debian (via apt)

```bash
sudo apt update
sudo apt install -y nginx libnginx-mod-rtmp
```

This pulls the official Ubuntu packages, which already include the RTMP module.

#### Option B – macOS (via Homebrew)

```bash
brew tap denji/nginx
brew install nginx-full --with-rtmp-module
```

If you are already using Homebrew nginx, replace it with the variant above so the RTMP module is available.

#### Option C – Build from source (any Linux)

If your distribution does not package `libnginx-mod-rtmp`, compile nginx with the module yourself:

```bash
sudo apt update && sudo apt install -y build-essential libpcre3 libpcre3-dev libssl-dev zlib1g-dev
curl -LO https://nginx.org/download/nginx-1.26.2.tar.gz
curl -LO https://github.com/arut/nginx-rtmp-module/archive/refs/heads/master.zip
tar -xzf nginx-1.26.2.tar.gz
unzip master.zip
cd nginx-1.26.2
./configure --with-http_ssl_module --add-module=../nginx-rtmp-module-master
make -j"$(nproc)"
sudo make install
```

Adjust the nginx version as needed. The compiled binary installs into `/usr/local/nginx` by default.

### 2. Copy the bundled configuration

Whichever installation path you used, replace the default configuration with the repo-provided RTMP settings. Copy
`nginx.conf` from the repository into your nginx configuration directory:

```bash
sudo cp nginx.conf /etc/nginx/nginx.conf             # Ubuntu/Debian package layout
sudo cp nginx.conf /usr/local/nginx/conf/nginx.conf  # Source build layout
```

If you prefer to keep the existing configuration, append the `rtmp { ... }` block from our file instead. Ensure the
`http` section exposes the status page on port `8080` and the `rtmp` section defines an `application live` block.

### 3. Open the firewall (optional but recommended)

Allow inbound traffic on the RTMP port (1935) and the status dashboard (8080) if you plan to access them remotely:

```bash
sudo ufw allow 1935/tcp
sudo ufw allow 8080/tcp
```

### 4. Start or reload nginx

```bash
# Using systemd managed nginx
sudo systemctl restart nginx

# Using the custom build
sudo /usr/local/nginx/sbin/nginx -s reload  # or -s stop/start for first run
```

Visit <http://localhost:8080> to confirm the status page loads and shows `RTMP Server Running`. From another terminal you can
verify the RTMP listener is active:

```bash
sudo ss -tulpn | grep 1935
```

### 5. Stream a test feed

Use FFmpeg to send a short test pattern to the server to verify the pipeline before running `drive_autostream.py`:

```bash
ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 -f lavfi -i sine=f=1000 -shortest \
  -c:v libx264 -preset veryfast -tune zerolatency -c:a aac -f flv rtmp://localhost/live/stream
```

Open VLC or OBS with `rtmp://localhost/live/stream` to confirm the feed. Once verified, proceed with the regular Google Drive
streaming flow described above.

#### Option D – Windows 10 (prebuilt bundle)

1. **Download a Windows build** of nginx with the RTMP module, such as the
   [nginx-rtmp-win32 releases](https://github.com/illuspas/nginx-rtmp-win32/releases).
   Grab the latest `nginx-rtmp-win32-<version>.zip` and extract it (for example
   to `C:\nginx-rtmp`).
2. **Replace the configuration** by copying this repository's `nginx.conf`
   over the extracted `conf\nginx.conf`.
3. **Launch the server** from an elevated PowerShell prompt:
   ```powershell
   cd C:\nginx-rtmp
   .\nginx.exe
   ```
   The command returns immediately because nginx continues running in the
   background. Use `./nginx.exe -s stop` to stop it or `./nginx.exe -s reload`
   after editing the configuration.
4. **Approve the firewall prompt** for `nginx.exe` the first time it starts so
   Windows can accept inbound connections on ports `1935` (RTMP) and `8080`
   (status page). To add the rule manually, run:
   ```powershell
   New-NetFirewallRule -DisplayName "nginx-rtmp" -Direction Inbound -Protocol TCP -LocalPort 1935,8080 -Action Allow
   ```
5. **Test the server** by sending a sample stream from the same machine:
   ```powershell
   ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 `
          -f lavfi -i sine=f=1000 -shortest `
          -c:v libx264 -preset veryfast -tune zerolatency `
          -c:a aac -f flv rtmp://localhost/live/stream
   ```
   Confirm playback in VLC/OBS at `rtmp://localhost/live/stream` or visit
   <http://localhost:8080> to ensure the RTMP status endpoint is live.

## Troubleshooting
- **`Unable to initialise Google Drive service`**: Check that `FOLDER_ID` is set and that the credentials JSON path is valid.
- **`Failed to retrieve Drive files`**: The service account may not have access to the folder; share the folder with the service account email.
- **FFmpeg exit codes**: Inspect the log output for codec or network errors. Ensure the downstream RTMP URLs are reachable and credentials are valid.
- **`error during connect: HEAD http://%2F...` when running Docker commands**: Follow [Fixing "error during connect"](#fixing-error-during-connect-head-http2f) to reset your Docker context or start Docker Desktop.

## License
This project is released under the MIT License.
