from discord import FFmpegOpusAudio
from loguru import logger
from yt_dlp import YoutubeDL

from .base import BaseTrack


class TrackStream(BaseTrack):
    def _initialize(self):
        try:
            ydl_opts = {
                **self._BASE_YD_OPTS,
                'http_headers': self._add_auth_headers(),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                }]
            }

            self.check_token_expiry()
            with YoutubeDL(ydl_opts) as ydl:
                self.info = ydl.extract_info(self.url, download=False)

                if not self.info: raise RuntimeError(f"Can\'t extract info from url: {self.url}")
        except Exception as e:
            logger.error(f"Stream initialization failed (yt-dlp): {str(e)}")
            raise

    async def create_source(self, *, start_time: int = 0):
        logger.debug("creating stream source")

        options = [
            '-vn',
            '-bufsize 512k',
            '-rtbufsize 2M',
            '-b:a 192k',
            '-max_delay 500000',
            f'-ss {start_time if start_time > 0 else 0}'
        ]
        self.start_pos = start_time
        logger.info(f"start_pos: {self.start_pos}")

        self.check_token_expiry()
        self.source = FFmpegOpusAudio(
            self.info['url'],
            before_options=[
                '-reconnect 1',
                '-reconnect_streamed 1',
                '-reconnect_delay_max 5',
                '-headers', '\r\n'.join(f'{k}: {v}' for k, v in self._COMMON_HEADERS.items()),
            ],
            options=options
        )

    def cleanup(self) -> None:
        try:
            if self.source:
                self.source.cleanup()
            logger.debug(f"Cleaned up audio source: {self.title}")
        except Exception as e:
            logger.error(f"Error cleaning source: {str(e)}")
        finally:
            self.source = None