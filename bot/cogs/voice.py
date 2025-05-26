from typing import Iterator, Optional
import asyncio
from time import time as _uix_time

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bot import GuardBot
from bot.cogs import voice_core


class VoiceCog(commands.Cog):
    def __init__(self, bot: GuardBot, voice_state_manager: voice_core.VoiceStateManager):
        self.bot: GuardBot = bot
        self.voice_state_manager: voice_core.VoiceStateManager = voice_state_manager
        voice_core.BaseTrack.load_credentials()

        self.execution_pause_time = 0
        self.execution_paused_time_passed = 0

    @staticmethod
    def refresh_token():
        voice_core.BaseTrack.load_credentials()
        voice_core.BaseTrack.check_token_expiry()

    @property
    def execution_paused_time_still(self):
        return self.execution_pause_time - self.execution_paused_time_passed

    @app_commands.command(
        name="join",
        description="подключиться к вашему каналу"
    )
    @app_commands.describe(force="позволяет перейти в канал")
    @app_commands.guild_only
    @GuardBot.error_handler(is_defer=True)
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

        await interaction.response.defer()  # type: ignore

        if not force and voice_state.current_channel:
            await interaction.followup.send(  # type: ignore
                f"Не могу! Сейчас я в канале: {voice_state.current_channel.mention}.",
                ephemeral=True
            )
        else:
            await voice_state.connect_or_move(user_voice.channel)

            try:
                await self._play_file(
                    interaction, voice_state, voice_core.TrackFile(
                        "data/the bluetooth device is ready to pair.mp3\n"
                        "bluetooth device\n"
                        "Server"
                    ), 3
                )
            finally:
                await interaction.followup.send(  # type: ignore
                    f"Зашёл в канал: {user_voice.channel.mention}."
                )

    @app_commands.command(
        name="disconnect",
        description="отключиться от канала"
    )
    @app_commands.describe(force="выйду из канала в любом случае")
    @app_commands.guild_only
    @GuardBot.error_handler(is_defer=True)
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

        await interaction.response.defer()  # type: ignore

        if voice_state.current_channel:
            if not force and voice_state.current_channel.id != user_voice.channel.id:
                await interaction.followup.send(  # type: ignore
                    f"Не могу! Я в другом канале: {voice_state.current_channel.mention}.",
                    ephemeral=True
                )
            else:

                try:
                    await self._play_file(
                        interaction, voice_state, voice_core.TrackFile(
                            "data/gaiti.mp3\n"
                            "gaiti\n"
                            "Server"
                        ), 3.6
                    )
                finally:
                    await interaction.followup.send(  # type: ignore
                        f"Выхожу из канала: {voice_state.current_channel.mention}."
                    )
                    await voice_state.disconnect()
        else:
            await interaction.followup.send(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(
        name="play",
        description="проигрывает YouTube ссылку без очереди"
    )
    @app_commands.describe(
        url="ссылка для проигрывания",
    )
    @app_commands.guild_only
    @GuardBot.error_handler(is_defer=True)
    async def play(self, interaction: discord.Interaction, url: str):
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
                try:
                    await self._play_file(
                        interaction, voice_state, voice_core.TrackFile(
                            "data/accepted.mp3\n"
                            "accepted\n"
                            "Server"
                        ), 3.6
                    )
                finally:
                    await self._play_audio_stream(interaction, voice_state, url)
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_stream(interaction, voice_state, url)

    @app_commands.command(
        name="add_track",
        description="добавляет YouTube ссылку в очередь"
    )
    @app_commands.describe(
        url="ссылка что я должен добавить в очередь",
    )
    @app_commands.guild_only
    @GuardBot.error_handler(is_defer=True)
    async def add_track(self, interaction: discord.Interaction, url: str):
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
                await self._add_track_to_queue(interaction, voice_state, url)
        else:
            await interaction.followup.send(  # type: ignore
                f"Захожу в канал {user_voice.channel.mention}, чтобы проиграть звук"
            )

            await voice_state.connect_or_move(user_voice.channel)

            await self._play_audio_stream(interaction, voice_state, url)

    async def _play_audio_stream(
            self,
            interaction: discord.Interaction,
            voice_state: voice_core.VoiceState,
            url: str
    ):
        if info := await voice_core.BaseTrack.check_playlist(url):
            return await self._handle_playlist(interaction, voice_state, info)

        track, load_message = await self._load_stream(interaction, url)

        try:
            logger.debug(f"start playing  {track.beautiful_title}")
            await load_message.edit(
                content=f"Воспроизвожу: **{track.beautiful_title}**"
            )

            await voice_state.play(track, interaction)
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{track.beautiful_title}**"
            )
            logger.error(f"error playing {track.beautiful_title}")
            raise

    async def _add_track_to_queue(
            self,
            interaction: discord.Interaction,
            voice_state: voice_core.VoiceState,
            url: str
    ):
        if info := await voice_core.BaseTrack.check_playlist(url):
            return await self._handle_playlist(interaction, voice_state, info)

        track, load_message = await self._load_stream(interaction, url)

        try:
            await voice_state.add_source(track)

            logger.debug(f"add to queue {url}")
            await load_message.edit(
                content=f"Добавил трэк  **{track.beautiful_title}** в очередь"
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
            voice_state: voice_core.VoiceState,
            playlist_info: dict
    ):
        if len(playlist_info['entries']) > 50:
            await interaction.followup.send(
                f"⚡ Слишком много треков, я загружу первые 50"
            )

        entries = playlist_info['entries'][:50]
        total = len(entries)

        added = 0
        errors = 0

        get_playlist_beautiful_title = lambda: (
            f"{playlist_info.get("channel", "Unknown Author")} - "
            f"{playlist_info.get('title', 'Unnamed')}"
        )

        start_load_message: discord.Message = await interaction.followup.send(
            f"🎶 Загружаю плейлист {get_playlist_beautiful_title()}\n"
            f"({total} треков)..."
        )
        content = f"✅ Добавлено `0/{total}` треков"
        load_message: discord.Message = await interaction.followup.send(
            f"✅ Добавлено `0/{total}` треков"
        )

        play_task: Optional[asyncio.Task] = None

        async for entry in self.iter_entry(entries):
            # checking loading
            if not entry.get('url'):
                continue
            if self.execution_pause_time:
                await interaction.followup.send(
                    f"Админ остановил загрузки плейлистов...",
                    ephemeral=True
                )
                break

            try:
                # load track
                track, _ = await self._load_stream(
                    interaction, entry['url'],
                    message=load_message, message_text=content
                )
                await voice_state.add_source(track)
                added += 1
                content = f"✅ Добавлено `{added}/{total}` треков" + (f"(не вышло `{errors}`)" if errors else "")
                await load_message.edit(
                    content=content +
                            f"\nзагрузил трек      `{entry['url']}`"
                )

                # play if not playing
                if not voice_state.is_playing:
                    play_task = asyncio.create_task(voice_state.play_next(interaction))
                    await interaction.followup.send(
                        f"Начинаю воспроизведение плейлиста **{get_playlist_beautiful_title()}** "
                        f"с трека: **{track.beautiful_title}**",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Playlist entry error: {type(e)}: {str(e)}")
                errors += 1

        if load_message:
            await load_message.delete()

        await start_load_message.edit(
            content=f"🎵 Плейлист **{get_playlist_beautiful_title()}** добавлен в очередь\n"
                    f"(`{added}` треков из `{total}`" + (f", не вышло `{errors}`)" if errors else ")")
        )

        if play_task:
            await play_task

    @staticmethod
    async def iter_entry(entries: dict[str, dict]) -> Iterator[dict]:
        for entry in entries:
            yield entry
            await asyncio.sleep(0.0)

    @staticmethod
    async def _load_stream(
            interaction: discord.Interaction, url: str,
            message: Optional[discord.Message] = None, message_text: str = ""
    ) -> tuple[voice_core.TrackStream, discord.Message]:
        try:
            if message:
                await message.edit(
                    content=message_text + "\n" + f"Подождите, загружаю `{url}`..."
                )
            else:
                message = await interaction.followup.send(
                    f"Подождите, загружаю `{url}`..."
                )

            return voice_core.TrackStream(url), message
        except Exception as e:
            logger.error(f"error load URL: {e}")
            await interaction.followup.send(
                f"Не вышло загрузить: `{url}`"
            )
            raise

    @staticmethod
    async def _play_file(
            interaction: discord.Interaction,
            voice_state: voice_core.VoiceState,
            track: voice_core.TrackFile,
            time: float
    ):
        try:
            await voice_state.stop()
            await voice_state.play(track, interaction)
            await asyncio.sleep(time)
        except:
            await interaction.followup.send(
                f"Не смог воспроизвести **{track.beautiful_title}**"
            )
            logger.error(f"error playing {track.beautiful_title}")
            raise

    @app_commands.command(
        name="remove_track",
        description="удаляет трек из очереди"
    )
    @app_commands.describe(
        index="номер трека в очереди"
    )
    @app_commands.guild_only
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

    @app_commands.command(
        name="play_next",
        description="пропускает трек"
    )
    @app_commands.guild_only
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
                elif voice_state.queue:
                    await interaction.response.send_message(  # type: ignore
                        f"Переключаюсь на **{voice_state.queue[0].beautiful_title}**"
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

    @app_commands.command(
        name="pause",
        description="пауза"
    )
    @app_commands.guild_only
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
                        f"Воспроизведение итак на паузе.",
                        ephemeral=True
                    )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(
        name="resume",
        description="продолжить"
    )
    @app_commands.guild_only
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
                    if voice_state.current_track:
                        await interaction.response.send_message(  # type: ignore
                            f"Продолжаю играть **{voice_state.current_track.beautiful_title}**."
                        )
                else:
                    await interaction.response.send_message(  # type: ignore
                        f"Воспроизведение не было на паузе.",
                        ephemeral=True
                    )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(
        name="stop",
        description="останавливает трек"
    )
    @app_commands.guild_only
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

    @app_commands.command(
        name="stop_all",
        description="останавливает играемый трек и очищает очередь"
    )
    @app_commands.guild_only
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

    @app_commands.command(
        name="show_queue",
        description="показывает очередь проигрывания"
    )
    @app_commands.guild_only
    @GuardBot.error_handler(is_defer=True)
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

                await interaction.response.defer(ephemeral=True)  # type: ignore

                if voice_state.current_track and voice_state.current_track.source:
                    resp = f"Сейчас играет: **{voice_state.current_track.beautiful_title}**\n"
                else:
                    resp = f"Сейчас ничего не играет\n"

                if voice_state.queue:
                    resp += "В очереди лежат:\n"

                    async for i, track in voice_state.iter_queue():
                        resp += (
                                f"> {i + 1}) " +
                                (f"**{track.beautiful_title}**\n" if track.info else f"`{track.url}`\n")
                        )

                await interaction.followup.send(  # type: ignore
                    GuardBot.normalize_response_size(resp),
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(
        name="clear_queue",
        description="очищает очередь проигрываний"
    )
    @app_commands.guild_only
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

                await voice_state.cleanup()

                await interaction.followup.send(  # type: ignore
                    "Очистил список воспроизведения"
                )
        else:
            await interaction.response.send_message(  # type: ignore
                "Не могу! Я не нахожусь ни в каком звуковом канале.",
                ephemeral=True
            )

    @app_commands.command(
        name="stop_voce_commands",
        description="(BETA) останавливает звуковых команды"
    )
    @app_commands.describe(
        time="время блокироыки (работает повторно)"
    )
    @app_commands.guild_only
    @GuardBot.has_permission(administrator=True)
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
    await bot.add_cog(
        VoiceCog(
            bot,
            voice_core.VoiceStateManager()
        )
    )
