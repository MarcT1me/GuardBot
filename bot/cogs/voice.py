from functools import partial
from typing import Optional
import os
import asyncio
from pprint import pformat

import discord
from discord import FFmpegOpusAudio
from discord import app_commands
from discord.ext import commands

from yt_dlp import YoutubeDL, DownloadError

from loguru import logger

from bot.bot import GuardBot


class TrackSource:
    ydl_opts = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
        },
        'extractor_args': {
            'youtube': {
                'skip': [
                    'authcheck'
                ]
            }
        },

        # search settings
        'format': 'bestaudio/best',
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'noplaylist': True,  # not allow playlists
        'quiet': True,  # quiet

        # connect
        'socket_timeout': 30,  # connection timeout
        'retries': 2,  # 2 attempts after error

        # file saving settings
        'outtmpl': 'bot_downloads_cache/%(title)s.%(ext)s',  # cache folder
        'restrictfilenames': True,  # remove not allow characters
        'final_ext': 'opus',

        # other
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
                'preferredquality': '192',
            }
        ],
        'verbose': False,
        'no_warnings': True,
        'cookiefile': 'cookies.txt',
    }

    def __init__(self, url: str):
        self.url: str = url
        with YoutubeDL(self.ydl_opts) as ydl:
            self.info: dict = ydl.extract_info(self.url, download=False)

        logger.info(f"track info:\n{pformat(self.info)}")

        self.filename: Optional[str] = None
        self.source: Optional[FFmpegOpusAudio] = None

    @property
    def title(self) -> str:
        return self.info["title"]

    @property
    def author(self) -> str:
        return self.info["channel"]

    @property
    def beautiful_title(self) -> str:
        return self.author + " - " + self.title

    @property
    def beautiful_data(self) -> tuple[str]:
        return (
            self.beautiful_title,
            self.info["like_count"],
            self.info["view_count"],
            self.info["comment_count"],
            self.info["timestamp"],
            self.info["uploaded_date"],
        )

    async def create_source(self) -> None:
        if not self.filename:
            await self._async_thread_download_audio()
        self.source = FFmpegOpusAudio(self.filename)

    async def download_audio(self) -> None:
        if self.filename:
            return

        await asyncio.to_thread(
            partial(self._async_thread_download_audio)
        )

    async def _async_thread_download_audio(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self._download_audio)
            )

            logger.debug(
                f" loaded:\n"
                f"title: {self.beautiful_title}\n"
                f"from file: {self.filename}"
            )

            if not os.path.exists(self.filename):
                raise FileNotFoundError("File not be downloaded!")
        except DownloadError as e:
            logger.error(f"Loading error url: {self.url}: {e}")
            raise
        except:
            logger.error(f"Loading error url: {self.url}")
            raise

    def _download_audio(self) -> None:
        with YoutubeDL(self.ydl_opts) as ydl:
            self.info = ydl.extract_info(self.url, download=True)
            self.filename = ydl.prepare_filename(self.info)
            self.filename = os.path.splitext(self.filename)[0] + '.opus'

    async def cleanup(self) -> None:
        if self.source:
            logger.debug(f"Deleting cache: {self.filename}")

            self.source.cleanup()
            self.source = None

            os.remove(self.filename)
            self.info = None
            self.filename = None


class VoiceState:
    def __init__(self):
        self._voice_client: Optional[discord.VoiceClient] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

        self.current_track: Optional[TrackSource] = None
        self.queue: list[TrackSource] = []

    @property
    def is_connected(self) -> bool:
        return self._voice_client.is_connected()

    @property
    def is_playing(self) -> bool:
        return self._voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self._voice_client.is_paused()

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

    async def play(self, track: str) -> None:
        if self._voice_client:
            await self.add_source(track, index=0)
            await self.play_next()

    async def add_source(self, track: TrackSource, index: int = None) -> None:
        if len(self.queue) < 2:
            await track.download_audio()

        if index:
            self.queue.insert(0, track)
        else:
            self.queue.append(track)

    async def play_next(self):
        if self.queue:
            await self._set_next()
            logger.info("play next track")
            await self._play_current()

    async def _set_next(self):
        if self.current_track:
            if self.is_playing:
                await self.stop()
            else:
                await self.current_track.cleanup()

        for i in range(min(2, len(self.queue))):
            await self.queue[i].download_audio()
            logger.info(f"Download track: {self.queue[i].beautiful_title}")

        next_track = self.queue.pop(0)
        self.current_track = next_track
        logger.info(f"set next track: {next_track.beautiful_title}")

    async def _play_current(self):
        if self._voice_client:
            await self.current_track.create_source()
            self._voice_client.play(self.current_track.source)
            logger.info(f"play track, {self.current_track.beautiful_title}")

    async def pause(self) -> None:
        if self._voice_client and self.is_playing:
            logger.info(f"pause track, {self.current_track.beautiful_title}")
            self._voice_client.pause()

    async def resume(self) -> None:
        if self._voice_client and self.is_paused:
            logger.info(f"resume track, {self.current_track.beautiful_title}")
            self._voice_client.resume()

    async def stop(self) -> None:
        if self._voice_client and self.is_playing:
            self._voice_client.stop()
            await self.current_track.cleanup()
            logger.info(f"stop track, {self.current_track.beautiful_title}")

    async def cleanup(self) -> None:
        if self.current_track:
            await self.current_track.cleanup()

        for track in self.queue:
            await track.cleanup()


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

    async def disconnect_all(self):
        for guild in self.bot.guilds:
            if voice_state := self.voice_state_manager.remove(guild.id):
                await voice_state.stop()
                await voice_state.cleanup()
                await voice_state.disconnect()

    @app_commands.command(name="join", description="connect to your channel")
    @GuardBot.error_handler
    async def join(self, interaction: discord.Interaction, force: bool = False):
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

            await interaction.response.send_message(  # type: ignore
                f"Зашёл в канал: {user_voice.channel.mention}."
            )

    @app_commands.command(name="disconnect", description="disconnect from your channel")
    @GuardBot.error_handler
    async def disconnect(self, interaction: discord.Interaction, force: bool = False):
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
                await interaction.response.send_message(  # type: ignore
                    f"Выхожу из канала: {voice_state.current_channel.name}."
                )
                await voice_state.disconnect()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="play", description="play YouTube url now")
    @GuardBot.error_handler
    async def play(self, interaction: discord.Interaction, url: str):
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

                while voice_state.queue and voice_state.is_connected:
                    await self._play_audio_main(interaction, voice_state, url)
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_main(interaction, voice_state, url)

    @app_commands.command(name="add_track", description="add YouTube url in queue")
    @GuardBot.error_handler
    async def add_track(self, interaction: discord.Interaction, url: str):
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
                    await self._add_track_to_queue(interaction, voice_state, url)
                except Exception:
                    raise
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_main(interaction, voice_state, url)

    @staticmethod
    async def _play_audio_main(interaction: discord.Interaction, voice_state: VoiceState, url: str):
        track = TrackSource(url)

        try:
            await track.download_audio()
        except:
            return await interaction.followup.send(
                f"Не вышло загрузить: **{track.beautiful_title}**"
            )

        try:
            logger.debug(f"start playing  {track.beautiful_title}")
            await interaction.followup.send(
                f"Воспроизвожу: **{track.beautiful_title}**"
            )

            await voice_state.play(track)
            await VoiceCog._playing_mainloop(interaction, voice_state)
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{track.beautiful_title}**"
            )
            logger.error(f"error playing {track.beautiful_title}")
            raise

    @staticmethod
    async def _playing_mainloop(interaction: discord.Interaction, voice_state: VoiceState):
        while voice_state.is_playing or not voice_state.is_paused:
            await asyncio.sleep(0.5)

            if not voice_state.is_connected: break
        else:
            if voice_state.current_track.filename not in [track.url for track in voice_state.queue]:
                await voice_state.current_track.cleanup()
            await voice_state.play_next()
            await interaction.followup.send(
                f"Проигрываю следующй трек **{voice_state.current_track.beautiful_title}**"
            )

    @staticmethod
    async def _add_track_to_queue(interaction: discord.Interaction, voice_state: VoiceState, url: str):
        track = TrackSource(url)

        try:
            await voice_state.add_source(track)

            logger.debug(f"add to queue {url}")
            await interaction.followup.send(
                f"Добавил " +
                f"и уже загрузил трэк  **{track.beautiful_title}**"
                if track.filename else
                f"трэк  **{track.beautiful_title}** в очередь на загрузку"
            )
        except:
            await interaction.followup.send(
                f"Не смог добавить  **{track.beautiful_title}** в список воспроизведений"
            )
            logger.error(f"error adding to queue  {track.beautiful_title}")
            raise

    @app_commands.command(name="pause", description="pause playing")
    @GuardBot.error_handler
    async def pause(self, interaction: discord.Interaction):
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

    @app_commands.command(name="resume", description="resume playing")
    @GuardBot.error_handler
    async def resume(self, interaction: discord.Interaction):
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

    @app_commands.command(name="stop", description="stop playing")
    @GuardBot.error_handler
    async def stop(self, interaction: discord.Interaction):
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

    @app_commands.command(name="play_next", description="skip playing track")
    @GuardBot.error_handler
    async def play_next(self, interaction: discord.Interaction):
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
                    f"Пропускаю **{voice_state.current_track.beautiful_title}**"
                )
                if voice_state.queue:
                    await voice_state.play_next()
                else:
                    await voice_state.stop()
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="show_queue", description="show audio queue")
    @GuardBot.error_handler
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

                if voice_state.current_track:
                    resp = f"Сейчас играет: {voice_state.current_track.beautiful_title}\n"
                else:
                    resp = f"Сейчас ничего не играет\n"

                if voice_state.queue:
                    resp += "В очереди лежат:\n"
                for i, track in enumerate(voice_state.queue):
                    resp += f"{i} - {track.beautiful_title}"

                await interaction.response.send_message(  # type: ignore
                    resp
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="clear_queue", description="clear audio queue")
    @GuardBot.error_handler
    async def clear_queue(self, interaction: discord.Interaction):
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

                voice_state.queue.clear()

                await interaction.response.send_message(  # type: ignore
                    "Очистил список воспроизведения"
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(name="stop_all", description="atop playing and clear queue")
    @GuardBot.error_handler
    async def stop_all(self, interaction: discord.Interaction):
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

                await voice_state.stop()
                await voice_state.cleanup()

                await interaction.response.send_message(  # type: ignore
                    "Очистил все воспроизведения"
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
                not after.channel and before.channel
                and voice_state.current_channel and voice_state.current_channel.id == before.channel.id
        ):
            self.voice_state_manager.remove(member.guild.id)
            await voice_state.disconnect()


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ VoiceCog loading")
    await bot.add_cog(VoiceCog(bot))
