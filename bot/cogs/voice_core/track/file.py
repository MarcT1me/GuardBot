from discord import FFmpegPCMAudio

from loguru import logger

from .base import BaseTrack


class TrackFile(BaseTrack):
    def _initialize(self):
        self.url = self.url.split("-_-")
        self.filename: str = self.url[0]
        self.info = {
            "title": self.url[1],
            "channel": self.url[2]
        }

        try:
            self.source = FFmpegPCMAudio(self.filename)
        except Exception as e:
            logger.error(f"Failed to create audio source: {str(e)}")
            raise

    def cleanup(self) -> None:
        pass
