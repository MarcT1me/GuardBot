from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
import os

import discord
from discord.ext import commands

from loguru import logger

from bot import GuardBot


class GuardLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.current_log_path: Optional[Path] = None
        self.last_flush_time: Optional[datetime] = None
        self.is_logging = False
        self.buffer: List[str] = []
        self.logger_id: Optional[int] = None
        self._setup_directory()

    def _setup_directory(self) -> None:
        self.log_dir.mkdir(exist_ok=True)

    def _generate_filename(self) -> str:
        return f"{datetime.now().strftime('%Y%m%d_%H_%M_%S')}.log"

    def _get_log_size(self) -> int:
        return os.path.getsize(self.current_log_path) if self.current_log_path else 0

    def _should_flush(self) -> bool:
        if not self.current_log_path:
            return False
        time_diff = datetime.now() - self.last_flush_time
        return len(self.buffer) >= 100 or time_diff.total_seconds() >= 3600

    def start_logging(self) -> None:
        if self.is_logging:
            return

        self.current_log_path = self.log_dir / self._generate_filename()
        self.is_logging = True
        self.last_flush_time = datetime.now()

        # Добавляем обработчик в loguru
        self.logger_id = logger.add(
            self.current_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            rotation=self._rotation_condition,
            retention=0,
            enqueue=True,
            backtrace=True
        )

    def stop_logging(self) -> None:
        if not self.is_logging:
            return

        self.is_logging = False
        if self.logger_id:
            logger.remove(self.logger_id)
        self._force_flush()

    def _rotation_condition(self, message) -> bool:
        return (
                self._get_log_size() + len(message.record["message"]) > 2000
                or datetime.now() - self.last_flush_time >= timedelta(hours=1)
        )

    def _force_flush(self) -> None:
        if self.current_log_path and self.buffer:
            with open(self.current_log_path, "a", encoding="utf-8") as f:
                f.write("\n".join(self.buffer))
            self.buffer.clear()

    def find_logs(self, start_time: datetime) -> List[Path]:
        logs = []
        for file in self.log_dir.glob("*.log"):
            try:
                file_time = datetime.strptime(file.stem, "%Y%m%d_%H_%M_%S")
                if file_time >= start_time:
                    logs.append(file)
            except ValueError:
                continue
        return sorted(logs)


class LoggingCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot = bot
        self.logger = GuardLogger()
        self.active_session: Optional[datetime] = None

    @commands.group()
    async def logs(self, ctx: commands.Context) -> None:
        """Управление логированием"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Используйте: !logs start/stop/get")

    @logs.command()
    async def start(self, ctx: commands.Context) -> None:
        """Начать новую сессию логирования"""
        self.logger.start_logging()
        self.active_session = datetime.now()
        await ctx.send(f"Логирование начато: {self.active_session.strftime('%Y-%m-%d %H:%M:%S')}")

    @logs.command()
    async def stop(self, ctx: commands.Context) -> None:
        """Остановить текущую сессию логирования"""
        self.logger.stop_logging()
        await ctx.send(f"Логирование остановлено. Сессия: {self.active_session.strftime('%Y-%m-%d %H:%M:%S')}")

    @logs.command()
    async def get(self, ctx: commands.Context, timestamp: str) -> None:
        """Получить логи с указанного времени (формат: YYYYMMDD_HHMMSS)"""
        try:
            start_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            found_logs = self.logger.find_logs(start_time)

            if not found_logs:
                await ctx.send("Логи не найдены")
                return

            await ctx.send(f"Найдено {len(found_logs)} лог-файлов:")
            for log_file in found_logs:
                await ctx.send(file=discord.File(log_file))

        except ValueError:
            await ctx.send("Неверный формат времени. Используйте: YYYYMMDD_HHMMSS")


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ LoggingCog loading")
    await bot.add_cog(LoggingCog(bot))
