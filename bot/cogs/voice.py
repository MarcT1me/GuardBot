from threading import Thread
from typing import Optional
import os
import asyncio
from time import time as _uix_time

import discord
from discord import FFmpegOpusAudio, FFmpegPCMAudio
from discord import app_commands
from discord.ext import commands

from yt_dlp import YoutubeDL

from loguru import logger

from bot.bot import GuardBot


class BaseTrack:
    _COOKIES_PROFILE = ('chrome', 'GuardBot')
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
        }
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


class TrackStream(BaseTrack):
    def _initialize(self):
        ydl_opts = {
            **self._BASE_YD_OPTS,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
            }],
            'verbose': True
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
            'verbose': False,
            'cookiefile': 'cookies.txt'
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
                self.filename
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


class TrackFile(BaseTrack):
    _download_thread: Optional[Thread]

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


class VoiceState:
    def __init__(self):
        self._voice_client: Optional[discord.VoiceClient] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

        self.current_track: Optional[TrackSource] = None
        self.queue: list[TrackSource] = []

    async def update_voice_client(self, channel: discord.VoiceChannel | discord.StageChannel):
        await self.connect_or_move(channel)

    @property
    def is_connected(self) -> bool:
        return self._voice_client and self._voice_client.is_connected()

    @property
    def is_playing(self) -> bool:
        return self._voice_client and self._voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self._voice_client and self._voice_client.is_paused()

    @property
    def current_channel(self) -> discord.VoiceChannel | discord.StageChannel | None:
        return self._current_channel

    async def connect_or_move(self, channel: discord.VoiceChannel) -> None:
        if self._voice_client and self.is_connected:
            await self._voice_client.move_to(channel)
            logger.info(f"Move to {channel.name}")
        else:
            self._voice_client = await channel.connect()  # type: ignore
            logger.info(f"Connecting to {channel.name}")

        self._current_channel = channel

    async def disconnect(self) -> None:
        if self._voice_client:
            if self.is_playing:
                await self.pause()

            await self._voice_client.disconnect()
            logger.info(f"Disconnecting from {self._current_channel.name}")

            self._voice_client = None
            self._current_channel = None

    async def play(self, track: str, interaction: discord.Interaction) -> None:
        if self._voice_client:
            await self.add_source(track, index=0)
            await self.play_next(interaction)

    async def add_source(self, track: TrackSource | TrackStream, index: int = None) -> None:
        if len(self.queue) < 2 and isinstance(track, TrackSource):
            track.download_audio()

        if index:
            self.queue.insert(0, track)
        else:
            self.queue.append(track)

    async def play_next(self, interaction):
        if not self.queue:
            logger.debug("Queue is empty")
            return

        logger.info("play next track")
        await self._set_next()
        await self._play_current(interaction)

    async def _set_next(self):
        if self.current_track:
            if self.is_playing:
                await self.stop()
            else:
                self.current_track.cleanup()

        for track in self.queue[:2]:
            if isinstance(track, TrackSource) and not track.filename:
                track.download_audio()
                logger.info(f"Download track: {track.beautiful_title}")

        if self.queue:
            next_track = self.queue.pop(0)
            self.current_track = next_track
            logger.info(f"set next track: {next_track.beautiful_title}")

    async def _play_current(self, interaction):
        if not self._voice_client or not self.current_track:
            return

        if isinstance(self.current_track, TrackSource):
            self.current_track.create_source()

        self._voice_client.play(
            self.current_track.source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.handle_playback(e, interaction),
                self._voice_client.loop
            )
        )
        logger.info(f"play track, {self.current_track.beautiful_title}")

    async def handle_playback(self, error: Optional[Exception], interaction: discord.Interaction):
        if error:
            return logger.error(f"Playback error: {str(error)}")

        if self.current_track:
            self.current_track.cleanup()
            self.current_track = None

        if self.queue:
            await interaction.followup.send(
                f"Переключаюсь на следующий трек **{self.queue[0].beautiful_title}**"
            )
            await self.play_next(interaction)
        else:
            logger.info("Queue is empty, stopping playback")
            await interaction.followup.send(
                f"Очередь воспроизведения кончилась"
            )

    async def pause(self) -> None:
        if self._voice_client and self.is_playing and self.current_track:
            logger.info(f"pause track, {self.current_track.beautiful_title}")
            self._voice_client.pause()

    async def resume(self) -> None:
        if self._voice_client and self.is_paused and self.current_track:
            logger.info(f"resume track, {self.current_track.beautiful_title}")
            self._voice_client.resume()

    async def stop(self) -> None:
        if self._voice_client and self.is_playing and self.current_track:
            self._voice_client.stop()
            logger.info(f"stop track, {self.current_track.beautiful_title}")
            self.current_track.cleanup()

    async def cleanup(self) -> None:
        if self.current_track:
            self.current_track.cleanup()

        for track in self.queue:
            track.cleanup()


class VoiceStateManager:
    def __init__(self):
        self.voice_states: dict[int, VoiceState] = {}

    def voice_state(self, guild_id: int) -> VoiceState:
        if guild_id not in self.voice_states:
            self.voice_states[guild_id] = VoiceState()
        return self.voice_states[guild_id]

    def remove(self, guild_id: int) -> VoiceState:
        if guild_id in self.voice_states:
            return self.voice_states.pop(guild_id)


class VoiceCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot = bot
        self.voice_state_manager = VoiceStateManager()

        self.execution_pause_time = 0
        self.execution_paused_time_passed = 0

    @property
    def execution_paused_time_still(self):
        return self.execution_pause_time - self.execution_paused_time_passed

    async def disconnect_all(self):
        for guild in self.bot.guilds:
            if voice_state := self.voice_state_manager.remove(guild.id):
                await voice_state.stop()
                await voice_state.cleanup()
                await voice_state.disconnect()

            for db_channel in await self.bot.db.get_channels(
                    server=await self.bot.db.get_server(guild_id=guild.id), channel_type="temp_voice"):
                await guild.get_channel(db_channel.id).delete(reason="channel auto-delete (disconnect_all)")
                await db_channel.delete()

    @app_commands.command(name="join", description="подключиться к вашему каналу")
    @app_commands.describe(force="Если поставить True - перейду в ваш канал при любых обстоятельствах")
    @GuardBot.error_handler()
    async def join(self, interaction: discord.Interaction, force: bool = False):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if not force and voice_state.current_channel:
            await interaction.response.send_message(  # type: ignore
                f"Не могу! Сейчас я в канале: {voice_state.current_channel.mention}.",
                ephemeral=True
            )
        else:
            await voice_state.connect_or_move(user_voice.channel)

            await interaction.response.defer()  # type: ignore

            await self._play_audio_file(
                interaction, voice_state, TrackFile(
                    "assets/the bluetooth device is ready to pair.mp3-_-"
                    "bluetooth device-_-"
                    "Server"
                ), 3
            )

            await interaction.followup.send(  # type: ignore
                f"Зашёл в канал: {user_voice.channel.mention}."
            )

    @app_commands.command(name="disconnect", description="отключиться от канала")
    @app_commands.describe(force="Если поставить True - выйду из канала в любом случае")
    @GuardBot.error_handler()
    async def disconnect(self, interaction: discord.Interaction, force: bool = False):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not force and not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if not force and voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.defer()  # type: ignore

                await self._play_audio_file(
                    interaction, voice_state, TrackFile(
                        "assets/gaiti.mp3-_-"
                        "gaiti-_-"
                        "Server"
                    ), 3.6
                )

                await interaction.followup.send(  # type: ignore
                    f"Выхожу из канала: {voice_state.current_channel.mention}."
                )
                await voice_state.disconnect()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="play", description="проигрывает YouTube ссылку без очереди")
    @app_commands.describe(
        url="ссылка для проигрывания",
        with_download="если поставить True - кеширует видео, что удлиняет загрузку, но уменьшает лаги"
    )
    @GuardBot.error_handler(is_defer=True)
    async def play(self, interaction: discord.Interaction, url: str, with_download: bool = False):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        await interaction.response.defer()  # type: ignore

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.followup.send(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                if voice_state.is_playing:
                    await voice_state.stop()

                await self._play_audio_file(
                    interaction, voice_state, TrackFile(
                        "assets/accepted.mp3-_-"
                        "accepted-_-"
                        "Server"
                    ), 3.6
                )

                await self._play_audio_main(interaction, voice_state, url, with_download)
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_main(interaction, voice_state, url, with_download)

    @app_commands.command(name="add_track", description="добавляет YouTube ссылку в очередь")
    @app_commands.describe(
        url="ссылка что я должен добавить в очередь",
        with_download="если поставить True - кеширует видео, что удлиняет загрузку, но уменьшает лаги"
    )
    @GuardBot.error_handler(is_defer=True)
    async def add_track(self, interaction: discord.Interaction, url: str, with_download: bool = False):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        await interaction.response.defer()  # type: ignore

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.followup.send(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                try:
                    await self._add_track_to_queue(interaction, voice_state, url, with_download)
                except Exception:
                    raise
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_main(interaction, voice_state, url, with_download)

    @app_commands.command(name="remove_track", description="удаляет трек из очереди")
    @app_commands.describe(index="номер трека в очереди (индексация с 1)")
    @GuardBot.error_handler()
    async def remove_track(self, interaction: discord.Interaction, index: int = 0):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                if queue := voice_state.queue:
                    if 0 > index >= len(queue):
                        return await interaction.response.send_message(  # type: ignore
                            "Индекс за пределами очереди!",
                            ephemeral=True
                        )

                    track = queue.pop(index - 1)

                    await interaction.response.send_message(  # type: ignore
                        f"Удаляю трек {track.beautiful_title}",
                        ephemeral=True
                    )

                    track.cleanup()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    async def _play_audio_main(
            self,
            interaction: discord.Interaction,
            voice_state: VoiceState,
            url: str,
            with_download: bool
    ):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    await self._handle_playlist(interaction, voice_state, info, with_download)
                    return

            message = await interaction.channel.send(
                f"Подождите, загружаю `{url}`..."
            )

            track = TrackSource(url) if with_download else TrackStream(url)

            if with_download:
                track.download_audio()

            await message.delete()
        except:
            logger.exception("error load URL")
            return await interaction.followup.send(
                f"Не вышло загрузить: `{url}`"
            )

        try:
            logger.debug(f"start playing  {track.beautiful_title}")
            await interaction.followup.send(
                f"Воспроизвожу: **{track.beautiful_title}**"
            )

            await voice_state.play(track, interaction)
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{track.beautiful_title}**"
            )
            logger.error(f"error playing {track.beautiful_title}")
            raise

    async def _play_audio_file(
            self,
            interaction: discord.Interaction,
            voice_state: VoiceState,
            track: TrackFile,
            time: float
    ):
        try:
            await voice_state.stop()
            voice_state._voice_client.play(track.source)
            await asyncio.sleep(time)
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{track.beautiful_title}**"
            )
            logger.error(f"error playing {track.beautiful_title}")
            raise

    async def _add_track_to_queue(
            self,
            interaction: discord.Interaction,
            voice_state: VoiceState,
            url: str,
            with_download: bool
    ):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    await self._handle_playlist(interaction, voice_state, info, with_download)
                    return

            track = TrackSource(url) if with_download else TrackStream(url)
        except:
            logger.exception("error load URL")
            return await interaction.followup.send(
                f"Не вышло загрузить: `{url}`"
            )

        try:
            await voice_state.add_source(track)

            logger.debug(f"add to queue {url}")
            await interaction.followup.send(
                f"Добавил трэк  **{track.beautiful_title}** в очередь"
            )
        except:
            await interaction.followup.send(
                f"Не смог добавить  **{track.beautiful_title}** в список воспроизведений"
            )
            logger.error(f"error adding to queue  {track.beautiful_title}")
            raise

    async def _handle_playlist(
            self,
            interaction: discord.Interaction,
            voice_state: VoiceState,
            playlist_info: dict,
            with_download: bool
    ):
        total = len(playlist_info['entries'])
        added = 0

        await interaction.followup.send(f"🎶 Начинаю загрузку плейлиста ({total} треков)...")

        load_message: discord.Message = None

        for entry in playlist_info['entries']:
            if not entry.get('url'):
                continue

            try:
                track = TrackSource(entry['url']) if with_download else TrackStream(entry['url'])
                await voice_state.add_source(track)
                added += 1

                if added % 5 == 0:
                    content = f"✅ Добавлено {added}/{total} треков"
                    if not load_message:
                        if self.execution_pause_time: break

                        load_message = await interaction.channel.send(content)
                        if not voice_state.is_playing:
                            interaction.followup.send(
                                f"Начинаю воспроизведение плейлиста с трэка {track.beautiful_title}"
                            )
                            await voice_state.play_next(interaction)

                    await load_message.edit(content=content)

            except Exception as e:
                logger.error(f"Playlist entry error: {str(e)}")

        await load_message.edit(content=f"✅ Добавлено {added}/{total} треков")

        await interaction.channel.send(
            f"🎵 Плейлист **{playlist_info.get('title', 'Unnamed')}** добавлен в очередь "
            f"({added} треков из {total})"
        )

        if not voice_state.is_playing:
            await voice_state.play_next(interaction)

    @app_commands.command(name="play_next", description="пропускает трек")
    @GuardBot.error_handler()
    async def play_next(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                if voice_state.current_track:
                    await interaction.response.send_message(  # type: ignore
                        f"Пропускаю **{voice_state.current_track.beautiful_title}**"
                    )
                else:
                    await interaction.response.send_message(  # type: ignore
                        f"Не могу, очередь пуста"
                    )

                if voice_state.queue:
                    await voice_state.play_next(interaction)
                else:
                    await voice_state.stop()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="pause", description="just пауза")
    @GuardBot.error_handler()
    async def pause(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                if voice_state.is_playing:
                    await voice_state.pause()
                    await interaction.response.send_message(  # type: ignore
                        f"Поставил на паузу **{voice_state.current_track.beautiful_title}**."
                    )
                else:
                    await interaction.response.send_message(  # type: ignore
                        f"Воспроизведение итак на паузе."
                    )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="resume", description="just продолжить")
    @GuardBot.error_handler()
    async def resume(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                if voice_state.is_paused:
                    await voice_state.resume()
                    await interaction.response.send_message(  # type: ignore
                        f"Продолжаю играть **{voice_state.current_track.beautiful_title}**."
                    )
                else:
                    await interaction.response.send_message(  # type: ignore
                        f"Воспроизведение не было на паузе."
                    )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="stop", description="останавливает трек")
    @GuardBot.error_handler()
    async def stop(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(  # type: ignore
                    f"Останавливаю воспроизведение **{voice_state.current_track.beautiful_title}**."
                )
                await voice_state.stop()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="stop_all", description="останавливает всё и играемый трек и очередь")
    @GuardBot.error_handler()
    async def stop_all(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                guild = interaction.guild
                voice_state = self.voice_state_manager.voice_state(guild.id)

                await interaction.response.defer()  # type: ignore

                await voice_state.stop()
                await voice_state.cleanup()

                await interaction.followup.send(  # type: ignore
                    "Очистил все воспроизведения"
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="show_queue", description="показывает очередь проигрывания")
    @GuardBot.error_handler()
    async def show_queue(self, interaction: discord.Interaction):
        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                guild = interaction.guild
                voice_state = self.voice_state_manager.voice_state(guild.id)

                await interaction.response.defer()  # type: ignore

                if voice_state.current_track and voice_state.current_track.source:
                    resp = f"Сейчас играет: **{voice_state.current_track.beautiful_title}**\n"
                else:
                    resp = f"Сейчас ничего не играет\n"

                if voice_state.queue:
                    resp += "В очереди лежат:\n"

                    for i, track in enumerate(voice_state.queue):
                        if isinstance(track, TrackStream):
                            status = 'S'
                        else:
                            status = 'R' if track.filename else 'L' if track.loading else 'Q'
                        resp += f"{i + 1} - {status} - **{track.beautiful_title}**\n"

                await interaction.followup.send(  # type: ignore
                    GuardBot.normalize_response_size(resp)
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="clear_queue", description="очищает только очередь проигрываний")
    @GuardBot.error_handler()
    async def clear_queue(self, interaction: discord.Interaction):
        if self.execution_pause_time:
            return await interaction.response.send_message(  # type: ignore
                f"Сейчас все войс команды приостановлены админом!"
                f"Подождите {int(self.execution_paused_time_still)} секунд",
                ephemeral=True
            )

        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                guild = interaction.guild
                voice_state = self.voice_state_manager.voice_state(guild.id)

                await interaction.response.defer()  # type: ignore

                voice_state.queue.clear()

                await interaction.followup.send(  # type: ignore
                    "Очистил список воспроизведения"
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="stop_voce_commands",
                          description="(BETA) останавливает выполнение части звуковых команд")
    @app_commands.describe(time="время на которое блокируются все войс команды (поыторый вызов перезаписывает время)")
    @GuardBot.error_handler()
    async def stop_voce_commands(self, interaction: discord.Interaction, time: float = 1.0):
        user_voice = interaction.user.voice
        if not user_voice:
            return await interaction.response.send_message(  # type: ignore
                "Не могу! Ты не в звуковом канале.",
                ephemeral=True
            )

        guild = interaction.guild
        voice_state = self.voice_state_manager.voice_state(guild.id)

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.defer()  # type: ignore

                await interaction.followup.send(  # type: ignore
                    "Останавливаю все войс команды"
                )

                self.execution_pause_time = time
                start_time = _uix_time()
                while self.execution_pause_time:
                    cur_time = _uix_time()
                    erl = cur_time - start_time
                    if erl >= time:
                        self.execution_paused_time_passed = 0
                        self.execution_pause_time = 0
                    else:
                        self.execution_paused_time_passed = erl
                    await asyncio.sleep(1)

                await interaction.followup.send(  # type: ignore
                    "Время прошло, можно снова использовать войс команды"
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return

        voice_state = self.voice_state_manager.voice_state(member.guild.id)
        if (
                not member.bot and not after.channel and before.channel and voice_state.current_channel
                and voice_state.current_channel.id == before.channel.id
                and len(before.channel.members) == 1
        ):
            self.voice_state_manager.remove(member.guild.id)
            await voice_state.stop()
            await voice_state.cleanup()
            await voice_state.disconnect()


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ VoiceCog loading")
    await bot.add_cog(VoiceCog(bot))
