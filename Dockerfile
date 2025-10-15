FROM ubuntu:22.04

RUN apt update && apt install -y \
    ffmpeg nginx libnginx-mod-rtmp python3 python3-pip && \
    apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY nginx.conf /etc/nginx/nginx.conf
COPY drive_autostream.py /app/drive_autostream.py

EXPOSE 1935 8080

CMD service nginx start && python3 /app/drive_autostream.py