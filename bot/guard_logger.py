from datetime import timedelta
import os
from typing import Optional

from loguru import logger


class GuardLogger:
    def __init__(self, *, log_dir: str = "logs", logging_active: bool = False):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.logging_active: bool = logging_active
        self.current_logger: Optional[int] = None

        if logging_active:
            self.start()

    def start(self):
        self.logging_active = True

        file_sink = str(self.log_dir) + "/{time:DD-MM-YYYY}.log"
        rotation = 2000000
        retention = timedelta(hours=1)

        self.current_logger = logger.start(
            sink=file_sink,
            encoding="utf-8",
            rotation=rotation,
            retention=retention,
        )

        logger.info("Логирование активировано")

    def stop(self):
        self.logging_active = False

        logger.info("Логирование остановлено")
        if self.current_logger:
            logger.remove(self.current_logger)
