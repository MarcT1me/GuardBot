import asyncio
from time import time as _uix_time

import discord
from discord import app_commands
from discord.ext import commands

from loguru import logger
from yt_dlp import YoutubeDL

from bot import GuardBot
from bot.cogs import voice_core


class VoiceCog(commands.Cog):
    def __init__(self, bot: GuardBot, voice_state_manager: voice_core.VoiceStateManager):
        self.bot: GuardBot = bot
        self.voice_state_manager: voice_core.VoiceStateManager = voice_state_manager

        self.execution_pause_time = 0
        self.execution_paused_time_passed = 0

    @property
    def execution_paused_time_still(self):
        return self.execution_pause_time - self.execution_paused_time_passed

    @app_commands.command(
        name="join",
        description="подключиться к вашему каналу"
    )
    @app_commands.describe(force="позволяет перейти в канал")
    @app_commands.guild_only
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
                interaction, voice_state, voice_core.TrackFile(
                    "assets/the bluetooth device is ready to pair.mp3-_-"
                    "bluetooth device-_-"
                    "Server"
                ), 3
            )

            await interaction.followup.send(  # type: ignore
                f"Зашёл в канал: {user_voice.channel.mention}."
            )

    @app_commands.command(
        name="disconnect",
        description="отключиться от канала"
    )
    @app_commands.describe(force="выйду из канала в любом случае")
    @app_commands.guild_only
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
                    interaction, voice_state, voice_core.TrackFile(
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

    @app_commands.command(
        name="play",
        description="проигрывает YouTube ссылку без очереди"
    )
    @app_commands.describe(
        url="ссылка для проигрывания",
        with_download="кеширует видео, +качество - скорость"
    )
    @app_commands.guild_only
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
                    interaction, voice_state, voice_core.TrackFile(
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

    @app_commands.command(
        name="add_track",
        description="добавляет YouTube ссылку в очередь"
    )
    @app_commands.describe(
        url="ссылка что я должен добавить в очередь",
        with_download="кеширует видео, +качество - скорость"
    )
    @app_commands.guild_only
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

    async def _play_audio_main(
            self,
            interaction: discord.Interaction,
            voice_state: voice_core.VoiceState,
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

            track = voice_core.TrackSource(url) if with_download else voice_core.TrackStream(url)

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
            voice_state: voice_core.VoiceState,
            track: voice_core.TrackFile,
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
            voice_state: voice_core.VoiceState,
            url: str,
            with_download: bool
    ):
        try:
            with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    await self._handle_playlist(interaction, voice_state, info, with_download)
                    return

            track = voice_core.TrackSource(url) if with_download else voice_core.TrackStream(url)
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
            voice_state: voice_core.VoiceState,
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
                track = voice_core.TrackSource(entry['url']) if with_download else voice_core.TrackStream(entry['url'])
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
                        f"Воспроизведение итак на паузе."
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
                        if isinstance(track, voice_core.TrackStream):
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

                voice_state.queue.clear()

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
