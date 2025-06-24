from typing import Any, Optional
import time

from discord import FFmpegOpusAudio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from yt_dlp import YoutubeDL
from loguru import logger


class BaseTrack:
    _COMMON_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'navigate',
        'Connection': 'keep-alive',
    }
    _BASE_YD_OPTS = {
        'format': 'bestaudio/best',

        'geo_bypass': True,

        'socket_timeout': 30,
        'retries': 20,
        'fragment_retries': 20,

        'ignoreerrors': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'skip': ['authcheck'],
                'player_client': ['web']
            }
        },
        'verbose': True,
    }

    _API_CREDENTIALS: Credentials = None
    _API_CREDENTIALS_LAST_UPDATE_TIME: float = 0

    @classmethod
    def load_credentials(cls, token_path="secret/token.json"):
        try:
            if not cls._API_CREDENTIALS:
                cls._API_CREDENTIALS = Credentials.from_authorized_user_file(token_path)
            logger.success(f"Client token - токен загружен из {token_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки токена: {str(e)}")

    @classmethod
    def check_token_expiry(cls, token_path="secret/token.json"):
        cur_time = time.time()
        if (
                cls._API_CREDENTIALS and cls._API_CREDENTIALS.expired or
                cur_time - cls._API_CREDENTIALS_LAST_UPDATE_TIME > 55 * 60
        ):
            cls._API_CREDENTIALS.refresh(Request())
            with open(token_path, 'w') as token_file:
                token_file.write(cls._API_CREDENTIALS.to_json())
            cls._API_CREDENTIALS_LAST_UPDATE_TIME = cur_time

    def __init__(self, url: str, info: dict = {}):
        self.url = url

        self.info: dict = info
        self.source: Optional[FFmpegOpusAudio] = None

        self._initialize() if not info else None

        self.playback_start: Optional[float] = None
        self.paused_duration: float = 0.0
        self.last_pause_time: Optional[float] = None
        self.start_pos = 0

    def _initialize(self):
        raise NotImplementedError

    async def create_source(self, *, start_time: int = 0):
        raise NotImplementedError

    def _add_auth_headers(self):
        if self._API_CREDENTIALS:
            return {
                **self._COMMON_HEADERS,
                'Authorization': f'Bearer {self._API_CREDENTIALS.token}'
            }
        return self._COMMON_HEADERS

    @classmethod
    async def check_playlist(cls, url: str) -> Any | None:
        try:
            cls.check_token_expiry()
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return info if 'entries' in info else None
        except Exception as e:
            logger.exception(f"Any error in playlist checking process: {e}")
            raise

    @property
    def duration(self) -> int:
        """Длительность трека в секундах"""
        if self.info:
            return self.info.get("duration", 0)
        logger.warning("Duration not found in info")
        return 0

    @property
    def beautiful_title(self) -> str:
        return f"{self.author} - {self.title}"

    @property
    def title(self) -> str:
        if self.info:
            return self.info.get("title", "Unknown Title")
        logger.warning("title not found in info")
        return "Unknown Title"

    @property
    def author(self) -> str:
        if self.info:
            return self.info.get("channel", "Unknown Author")
        logger.warning("channel not found in info")
        return "Unknown Author"

    @property
    def duration(self) -> int:
        if self.info:
            return self.info.get("duration", 0)
        logger.warning("duration not found in info")
        return 0

    def cleanup(self) -> None:
        raise NotImplementedError
