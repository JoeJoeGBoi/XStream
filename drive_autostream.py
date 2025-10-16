"""Google Drive to multi-platform RTMP restreamer.

This module wires together configuration loading, Google Drive discovery and
FFmpeg tee streaming so a folder full of videos can be continuously broadcast
to one or more RTMP targets.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class StreamConfig:
    """Holds all values required to authenticate and stream videos."""

    folder_id: str
    service_account_file: Path
    refresh_interval: int = 600
    stream_key: str = 'stream'
    youtube_url: str | None = None
    twitch_url: str | None = None

    @classmethod
    def from_sources(cls, args: argparse.Namespace) -> 'StreamConfig':
        """Build a configuration using CLI flags with environment fallbacks."""

        folder_id = args.folder_id or os.getenv('FOLDER_ID')
        if not folder_id:
            raise ConfigurationError(
                'Missing Google Drive folder ID. Provide --folder-id or set '
                'the FOLDER_ID environment variable.'
            )

        service_account = args.service_account_file or os.getenv(
            'SERVICE_ACCOUNT_FILE', '/app/credentials.json'
        )
        service_account_path = Path(service_account).expanduser()
        if not service_account_path.is_file():
            raise ConfigurationError(
                f"Service account file not found at '{service_account_path}'. "
                'Set SERVICE_ACCOUNT_FILE or pass --service-account-file.'
            )

        refresh_interval = _parse_refresh_interval(args.refresh_interval)

        return cls(
            folder_id=folder_id,
            service_account_file=service_account_path,
            refresh_interval=refresh_interval,
            stream_key=args.stream_key or os.getenv('RTMP_STREAM_KEY', 'stream'),
            youtube_url=args.youtube_url or os.getenv('YOUTUBE_URL') or None,
            twitch_url=args.twitch_url or os.getenv('TWITCH_URL') or None,
        )

    @property
    def local_rtmp_url(self) -> str:
        return f"rtmp://localhost/live/{self.stream_key}"

    @property
    def tee_targets(self) -> List[str]:
        targets: List[str] = [self.local_rtmp_url]
        if self.youtube_url:
            targets.append(self.youtube_url)
        if self.twitch_url:
            targets.append(self.twitch_url)
        return targets


def _parse_refresh_interval(cli_value: int | None) -> int:
    """Resolve the refresh interval from CLI or environment values."""

    if cli_value is not None:
        refresh_interval = cli_value
    else:
        refresh_interval_str = os.getenv('REFRESH_INTERVAL', '600')
        try:
            refresh_interval = int(refresh_interval_str)
        except ValueError as exc:  # noqa: B904 - add context for the user
            raise ConfigurationError(
                f"REFRESH_INTERVAL must be an integer, got '{refresh_interval_str}'."
            ) from exc

    if refresh_interval <= 0:
        raise ConfigurationError('Refresh interval must be a positive integer.')

    return refresh_interval


def ensure_ffmpeg_available() -> None:
    """Verify ffmpeg is on PATH before attempting to stream."""

    if shutil.which('ffmpeg') is None:
        raise ConfigurationError(
            'ffmpeg executable not found on PATH. Install ffmpeg and retry.'
        )


def load_drive_service(config: StreamConfig):
    """Create an authenticated Google Drive service client."""

    credentials = service_account.Credentials.from_service_account_file(
        str(config.service_account_file), scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)


def fetch_drive_videos(drive_service, folder_id: str) -> List[Dict[str, str]]:
    """Retrieve video metadata for the configured folder."""

    try:
        results = (
            drive_service
            .files()
            .list(
                q=f"'{folder_id}' in parents and mimeType contains 'video/'",
                pageSize=1000,
                fields="files(id, name)",
                orderBy='name',
            )
            .execute()
        )
    except HttpError as exc:
        logging.warning("Failed to retrieve Drive files: %s", exc)
        return []

    files = results.get('files', [])
    files.sort(key=lambda entry: entry.get('name', ''))
    return files


def build_tee_output(targets: Iterable[str]) -> str:
    """Construct the ffmpeg tee muxer string for the configured outputs."""

    return f"[f=flv]{'|'.join(targets)}"


def stream_videos(files: List[Dict[str, str]], config: StreamConfig) -> None:
    """Iterate through Drive files and relay each via ffmpeg."""

    tee_output = build_tee_output(config.tee_targets)
    for index, file_info in enumerate(files, start=1):
        file_id = file_info['id']
        name = file_info.get('name', file_id)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        logging.info("Streaming %s/%s: %s", index, len(files), name)

        ffmpeg_cmd = [
            'ffmpeg', '-re', '-i', url,
            '-c:v', 'libx264', '-preset', 'veryfast',
            '-c:a', 'aac', '-ar', '44100', '-b:a', '128k',
            '-f', 'tee', tee_output,
        ]

        logging.debug("Running command: %s", ' '.join(ffmpeg_cmd))
        try:
            result = subprocess.run(ffmpeg_cmd, check=False, text=False)
            if result.returncode != 0:
                logging.warning(
                    "ffmpeg exited with code %s while streaming %s.",
                    result.returncode,
                    name,
                )
        except Exception as exc:  # noqa: BLE001 - catch runtime issues to continue
            logging.exception("Error streaming %s: %s", name, exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Restream Google Drive videos to RTMP destinations.',
    )
    parser.add_argument('--folder-id', help='Google Drive folder ID to stream.')
    parser.add_argument(
        '--service-account-file',
        help='Path to the Google service account credentials JSON.',
    )
    parser.add_argument(
        '--refresh-interval',
        type=int,
        help='Seconds to wait before checking Drive for new files.',
    )
    parser.add_argument(
        '--stream-key',
        help='Local RTMP stream key. Defaults to RTMP_STREAM_KEY env or "stream".',
    )
    parser.add_argument('--youtube-url', help='Optional RTMP endpoint for YouTube.')
    parser.add_argument('--twitch-url', help='Optional RTMP endpoint for Twitch.')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Stream the playlist a single time then exit.',
    )
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        help='Logging level (DEBUG, INFO, WARNING, ERROR).',
    )
    return parser


def run(config: StreamConfig, *, drive_service, run_once: bool) -> None:
    """Main streaming loop."""

    logging.info("Drive Auto-Stream initialised. Monitoring folder %s.", config.folder_id)
    try:
        while True:
            files = fetch_drive_videos(drive_service, config.folder_id)
            if not files:
                logging.warning(
                    "No videos found. Retrying in %s seconds...",
                    config.refresh_interval,
                )
                if run_once:
                    break
                time.sleep(config.refresh_interval)
                continue

            logging.info("Found %s videos. Beginning broadcast...", len(files))
            stream_videos(files, config)

            if run_once:
                logging.info("Single-pass run complete.")
                break

            minutes = config.refresh_interval // 60
            logging.info(
                "Playlist done. Rechecking in %s minute%s.",
                minutes or config.refresh_interval,
                '' if minutes == 1 else 's',
            )
            time.sleep(config.refresh_interval)
    except KeyboardInterrupt:
        logging.info("Received interrupt. Shutting down cleanly...")


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(asctime)s | %(levelname)s | %(message)s',
    )

    try:
        ensure_ffmpeg_available()
        config = StreamConfig.from_sources(args)
        drive_service = load_drive_service(config)
    except ConfigurationError as exc:
        logging.error("Configuration error: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - surface friendly error message
        logging.exception("Unable to initialise Google Drive service: %s", exc)
        return 1

    run(config, drive_service=drive_service, run_once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
