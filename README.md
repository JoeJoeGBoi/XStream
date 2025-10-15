🧩 Step 1: Get a Google Drive API Key or OAuth Token

To list files programmatically, you need Google Drive API access.
You can use either:

A service account (for automated / headless use), or

A personal OAuth token (if you’re streaming from your own Drive).

Here’s how to get one:

Go to Google Cloud Console
.

Enable the Google Drive API.

Create a Service Account or OAuth client credentials.

Download the credentials JSON file (e.g., credentials.json).


🧠 Step 5: Viewing or Relaying the Stream

View locally:

vlc rtmp://localhost/live/stream


Re-broadcast to YouTube (optional):

ffmpeg -i rtmp://localhost/live/stream \
       -c copy -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY


Or, integrate into OBS as a Media Source → Input: RTMP URL.
