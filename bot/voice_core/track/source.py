import os
from threading import Thread
from typing import Optional

from discord import FFmpegOpusAudio

from loguru import logger
from yt_dlp import YoutubeDL

from .base import BaseTrack


class TrackSource(BaseTrack):
    _download_thread: Optional[Thread]

    def _initialize(self):
        self.ydl_opts = {
            **self._BASE_YD_OPTS,
            'outtmpl': 'bot_downloads_cache/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': '192',
            }],
            'restrictfilenames': True,
        }

        self._download_thread: Optional[Thread] = None
        self.filename: Optional[str] = None

        try:
            with YoutubeDL(self.ydl_opts) as ydl:
                self.info = ydl.extract_info(self.url, download=False)
                if not self.info:
                    raise RuntimeError("Failed to extract track info")
        except Exception as e:
            logger.error(f"TrackSource init failed: {str(e)}")
            raise

    def create_source(self) -> None:
        if not self.filename:
            self.download_audio()

        try:
            if self._download_thread: self._download_thread.join()
            self.source = FFmpegOpusAudio(
                self.filename,
                before_options=[
                    '-reconnect 20',
                    '-reconnect_streamed 20',
                    '-reconnect_delay_max 30',
                    # '-headers', '\r\n'.join(f'{k}: {v}' for k, v in self._COMMON_HEADERS.items())
                ],
                options=['-vn -b:a 192k']
            )
        except Exception as e:
            logger.error(f"Failed to create audio source: {str(e)}")
            raise

    def download_audio(self) -> None:
        if self._download_thread and self._download_thread.is_alive():
            logger.warning(f"Download already in progress for {self.beautiful_title}")
            return

        if self.filename and os.path.exists(self.filename):
            logger.debug(f"File already exists: {self.filename}")
            return

        self._download_thread = Thread(target=self._download_audio, daemon=True)
        self._download_thread.start()

    def _download_audio(self) -> None:
        if self.loading: return

        try:
            self.loading = True

            with YoutubeDL(self.ydl_opts) as ydl:
                self.info = ydl.extract_info(self.url, download=True)
                self.filename = ydl.prepare_filename(self.info)
                self.filename = os.path.splitext(self.filename)[0] + '.opus'

            if os.path.getsize(self.filename) < 1024:
                raise ValueError("Invalid file size")

            logger.debug(
                f" loaded:\n"
                f"title: {self.beautiful_title}\n"
                f"from file: {self.filename}"
            )

            if not self.filename or not os.path.exists(self.filename):
                raise FileNotFoundError("File not be downloaded!")
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            if self.filename and os.path.exists(self.filename):
                os.remove(self.filename)
            raise
        finally:
            self.loading = False

    def cleanup(self) -> None:
        super().cleanup()
        if self.filename and os.path.exists(self.filename):
            try:
                os.remove(self.filename)
                logger.debug(f"Deleted file: {self.filename}")
            except Exception as e:
                logger.error(f"File deletion error: {str(e)}")
            finally:
                self.filename = None
