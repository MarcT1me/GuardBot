import os
from typing import Optional

from discord import FFmpegOpusAudio
from loguru import logger


class BaseTrack:
    _COOKIES_PROFILE = ("chrome", "Profile 5")
    _COMMON_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'navigate',
        'Connection': 'keep-alive',
    }
    _BASE_YD_OPTS = {
        'cookies_from_browser': _COOKIES_PROFILE,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'socket_timeout': 30,
        'retries': 20,
        'fragment_retries': 20,
        'ignoreerrors': True,
        'noplaylist': True,
        'http_headers': _COMMON_HEADERS,
        'extractor_args': {
            'youtube': {
                'skip': ['authcheck'],
                'player_client': ['android', 'web']
            }
        },
        'verbose': True,
    }
    filename = False
    loading = False

    def __init__(self, url: str):
        self.url = url

        self.info: dict = None
        self.source: Optional[FFmpegOpusAudio] = None

        self._initialize()

    def _initialize(self):
        raise NotImplementedError

    @property
    def title(self) -> str:
        return self.info.get("title", "Unknown Title")

    @property
    def author(self) -> str:
        return self.info.get("channel", "Unknown Author")

    @property
    def beautiful_title(self) -> str:
        return f"{self.author} - {self.title}"

    def cleanup(self) -> None:
        if self.source:
            try:
                self.source.cleanup()
                logger.debug(f"Cleaned up audio source: {self.title}")
            except Exception as e:
                logger.error(f"Error cleaning source: {str(e)}")
            finally:
                self.source = None
