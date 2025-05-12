from functools import partial
from typing import Optional
import os
import asyncio

import discord
from discord import FFmpegOpusAudio
from discord import app_commands
from discord.ext import commands

from yt_dlp import YoutubeDL, DownloadError

from loguru import logger

from bot.bot import GuardBot


class VoiceState:
    def __init__(self, guild_id: int):
        self.guild_id: int = guild_id
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_player: Optional[FFmpegOpusAudio] = None
        self.current_played_filename: Optional[str] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

    @property
    def is_connected(self) -> bool:
        return self.voice_client.is_connected()

    @property
    def is_playing(self) -> bool:
        return self.voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self.voice_client.is_paused()

    @property
    def current_channel(self) -> discord.VoiceChannel | discord.StageChannel | None:
        return self._current_channel

    async def connect_or_move(self, channel: discord.VoiceChannel) -> None:
        if self.voice_client and self.is_connected:
            await self.voice_client.move_to(channel)
            logger.info(f"Move to {channel.name}")
        else:
            self.voice_client = await channel.connect()  # type: ignore
            logger.info(f"Connecting to {channel.name}")

        self._current_channel = channel

    async def disconnect(self) -> None:
        if self.voice_client:
            if self.is_playing:
                await self.stop()

            await self.voice_client.disconnect()
            logger.info(f"Disconnecting from {self._current_channel.name}")

            self.voice_client = None
            self._current_channel = None

    async def play_source(self, source: FFmpegOpusAudio, filename: str) -> None:
        if self.voice_client:
            self.current_player = source
            self.current_played_filename = filename

            self.voice_client.play(source)

            try:
                while self.is_playing: await asyncio.sleep(0.5)
                self.cleanup()
            except Exception as e:
                raise RuntimeError(f"File deleting error: {filename}") from e

    async def pause(self) -> None:
        if self.voice_client and self.is_playing:
            self.voice_client.pause()

    async def resume(self) -> None:
        if self.voice_client and self.is_paused:
            self.voice_client.resume()

    async def stop(self) -> None:
        if self.voice_client and self.is_playing:
            self.voice_client.stop()
            self.cleanup()

    def cleanup(self) -> None:
        if self.current_player:
            logger.debug(f"Deleting cache: {self.current_played_filename}")

            self.current_player.cleanup()
            self.current_player = None

            os.remove(self.current_played_filename)
            self.current_played_filename = None


class VoiceStateManager:
    def __init__(self):
        self.voice_states: dict[int, VoiceState] = {}

    def voice_state(self, guild_id: int) -> VoiceState:
        if guild_id not in self.voice_states:
            self.voice_states[guild_id] = VoiceState(guild_id)
        return self.voice_states[guild_id]

    def remove(self, guild_id: int) -> VoiceState:
        if guild_id in self.voice_states:
            return self.voice_states.pop(guild_id)


class VoiceCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot = bot
        self.voice_state_manager = VoiceStateManager()
        self.ydl_opts = {
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

    async def disconnect_all(self):
        for guild in self.bot.guilds:
            if voice_state := self.voice_state_manager.remove(guild.id):
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

    @app_commands.command(name="play", description="play YouTube url")
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

        if voice_state.current_channel:
            if voice_state.current_channel.id != user_voice.channel.id:
                await interaction.response.send_message(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:
                try:
                    if voice_state.is_playing:
                        await voice_state.stop()

                    await self._play_audio_main(interaction, voice_state, url)
                except Exception:
                    raise
        else:
            await interaction.channel.send(
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_main(interaction, voice_state, url)

    async def _play_audio_main(self, interaction: discord.Interaction, voice_state: VoiceState, url: str):
        await interaction.response.defer()  # type: ignore

        info, filename = await self._async_safe_download_audio(interaction, url)

        if not os.path.exists(filename): raise FileNotFoundError("File not be downloaded!")

        await self._async_safe_play_sound(interaction, voice_state, info, filename)

    @staticmethod
    async def _async_safe_play_sound(interaction: discord.Interaction, voice_state: VoiceState,
                                     info: dict, filename: str):
        try:
            logger.debug(f"start playing {info['title']}")
            await interaction.followup.send(
                f"Воспроизвожу: **{info['title']}**"
            )
            await voice_state.play_source(
                FFmpegOpusAudio(filename), filename
            )
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{info['title']}**"
            )
            logger.error(f"error playing {info['title']}")
            raise

    async def _async_safe_download_audio(self, interaction, url) -> tuple[dict, str]:
        try:
            loop = asyncio.get_event_loop()
            info, filename = await loop.run_in_executor(
                None,
                partial(self._download_audio, url)
            )
            logger.debug(
                f" loaded:\n"
                f"title: {info['title']}\n"
                f"from file: {filename}"
            )
            return info, filename
        except DownloadError as e:
            await interaction.followup.send(f"Не смог загрузить `{url}`: {e}")
            logger.error(f"Loading error url: {url}: {e}")
        except:
            await interaction.followup.send(f"Не смог загрузить `{url}`")
            logger.error(f"Loading error url: {url}")
            raise

    def _download_audio(self, url: str):
        with YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filename = os.path.splitext(filename)[0] + '.opus'
            return info, filename

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
                        f"Воспроизведение поставлено на паузу."
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
                        f"Воспроизведение убрано с паузы."
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
                    f"Останавливаю воспроизведение."
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
        if not after.channel and before.channel and voice_state.current_channel.id == before.channel.id:
            self.voice_state_manager.remove(member.guild.id)
            await voice_state.disconnect()


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ VoiceCog loading")
    await bot.add_cog(VoiceCog(bot))
