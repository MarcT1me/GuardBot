from discord import FFmpegOpusAudio

from loguru import logger
from yt_dlp import YoutubeDL

from .base import BaseTrack


class TrackStream(BaseTrack):
    def _initialize(self):
        ydl_opts = {
            **self._BASE_YD_OPTS,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
            }]
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                self.info = ydl.extract_info(self.url, download=False)
                self.source_url = self.info['url']
                self.source = self._create_audio_source()
        except Exception as e:
            logger.error(f"Stream initialization failed: {str(e)}")
            raise

    def _create_audio_source(self):
        return FFmpegOpusAudio(
            self.source_url,
            before_options=[
                '-reconnect 20',
                '-reconnect_streamed 20',
                '-reconnect_delay_max 30',
                '-headers', '\r\n'.join(f'{k}: {v}' for k, v in self._COMMON_HEADERS.items())
            ],
            options=['-vn -b:a 192k']
        )
