import asyncio
from typing import Optional, Iterator
import time

import discord
from loguru import logger

from bot import GuardBot
from .track import BaseTrack, TrackFile


class VoiceState:
    def __init__(self):
        self._voice_client: Optional[discord.VoiceClient] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

        self.current_track: Optional[BaseTrack] = None
        self.queue: list[BaseTrack] = []

        self._is_active = False
        self._seek_loading = False
        self._is_play_when_disconnect = False

        self._start_time: Optional[float] = None
        self._paused_time: Optional[float] = None
        self._seek_offset: int = 0

    async def update_voice_client(self, channel: discord.VoiceChannel | discord.StageChannel):
        await self.connect_or_move(channel)

    @property
    def is_connected(self) -> bool:
        return self._voice_client and self._voice_client.is_connected()

    @property
    def is_playing(self) -> bool:
        return self._voice_client and self._voice_client.is_playing()

    @property
    def is_play_when_disconnect(self):
        return self._is_play_when_disconnect

    @property
    def is_paused(self) -> bool:
        return self._voice_client and self._voice_client.is_paused()

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def current_channel(self) -> discord.VoiceChannel | discord.StageChannel | None:
        return self._current_channel

    @property
    def current_position(self) -> int:
        if not self._start_time:
            return 0

        if self._paused_time:
            return int(self._paused_time - self._start_time + self._seek_offset)

        return int(time.time() - self._start_time + self._seek_offset)

    async def iter_queue(self) -> Iterator[BaseTrack]:
        for i, track in enumerate(self.queue):
            yield i, track
            await asyncio.sleep(0.0)

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
                self._is_play_when_disconnect = True
                self._seek_offset = self.current_position
                await self.stop()

            await self._voice_client.disconnect()
            logger.info(f"Disconnecting from {self._current_channel.name}")

            self._voice_client = None
            self._current_channel = None

    async def seek(self, seconds: int):
        if self.current_track and self._voice_client:
            self._seek_offset = seconds
            self._is_play_when_disconnect = False

            self._seek_loading = True
            current_track = self.current_track
            await self.stop()
            self.current_track = current_track
            await self.current_track.create_source(start_time=seconds)

            self._start_time = time.time()
            self._voice_client.play(self.current_track.source)

            self._seek_loading = False

    async def play(self, track: BaseTrack, interaction: discord.Interaction) -> None:
        if self._voice_client:
            if isinstance(track, TrackFile):
                return self._voice_client.play(track.source)
            await self.add_source(track, index=0)
            await self.play_next(interaction)

    async def add_source(self, track: BaseTrack, index: int = None) -> None:
        if index:
            self.queue.insert(index, track)
        else:
            self.queue.append(track)

    async def play_next(self, interaction):
        if not self._is_active:
            await self._play_loop(interaction)
        elif self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()

    async def _play_loop(self, interaction):
        self._is_active = True
        while self._is_active and self.queue:
            await self._set_next()
            await self._play_current(interaction)

            # Ожидаем завершения текущего трека
            while (self._voice_client and self._voice_client.is_playing()) or self._seek_loading:
                await asyncio.sleep(0.0)

            if self.queue:
                await interaction.followup.send(
                    f"Переключаюсь на следующий трек **{self.queue[0].beautiful_title}**"
                )

        self._is_active = False
        if not self.queue:
            await interaction.followup.send("Очередь воспроизведения кончилась")

    async def _set_next(self):
        if self.current_track:
            await self.stop()

        if self.queue:
            next_track = self.queue.pop(0)
            await next_track.create_source()
            self.current_track = next_track
            logger.info(f"set next track: {next_track.beautiful_title}")

    async def _play_current(self, interaction):
        if not self._voice_client or not self.current_track:
            return

        self._start_time = time.time()
        self._paused_time = None
        self._seek_offset = 0
        self._is_play_when_disconnect = False

        self._voice_client.play(
            self.current_track.source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self._handle_playback(e, interaction),
                self._voice_client.loop
            )
        )
        logger.info(f"play track, {self.current_track.beautiful_title}")

    async def _handle_playback(self, error: Optional[Exception], interaction: discord.Interaction):
        if error:
            logger.error(f"Playback error: {str(error)}")
            return await interaction.followup.send(f"Ошибка воспроизведения: {str(error)}")

        if self.current_track and (not self._is_play_when_disconnect or not self._seek_loading):
            self.current_track.cleanup()
            self.current_track = None

    async def pause(self) -> None:
        if self.is_playing and self.current_track:
            logger.info(f"pause track, {self.current_track.beautiful_title}")
            self._paused_time = time.time()
            self._voice_client.pause()

    async def resume(self) -> None:
        if self.is_paused and self.current_track:
            logger.info(f"resume track, {self.current_track.beautiful_title}")
            if self._is_play_when_disconnect:
                await self.seek(self._seek_offset)
            else:
                self._is_play_when_disconnect = False
                self._seek_offset += time.time() - self._paused_time
                self._voice_client.resume()

    async def stop(self) -> None:
        self._is_active = False

        if self.is_playing:
            self._voice_client.stop()
        if self.current_track:
            logger.info(f"stop track, {self.current_track.beautiful_title}")
            self.current_track.cleanup()
            self.current_track = None

    async def cleanup(self) -> None:
        self._is_active = False

        if self.current_track:
            self.current_track.cleanup()

        for i in range(len(self.queue)):
            self.queue.pop().cleanup()


class VoiceStateManager:
    def __init__(self):
        self.voice_states: dict[int, VoiceState] = {}

    async def disconnect_all(self):
        for guild in GuardBot.instance.guilds:
            if voice_state := self.remove(guild.id):
                await voice_state.stop()
                await voice_state.cleanup()
                await voice_state.disconnect()

            for db_channel in await GuardBot.instance.db.get_channels(
                    server=await GuardBot.instance.db.get_server(guild_id=guild.id), channel_type="temp_voice"
            ):
                await db_channel.delete()
                if channel := guild.get_channel(db_channel.id):
                    await channel.delete(reason="channel auto-delete (disconnect_all)")

    def voice_state(self, guild_id: int) -> VoiceState:
        if guild_id not in self.voice_states:
            self.voice_states[guild_id] = VoiceState()
        return self.voice_states[guild_id]

    def remove(self, guild_id: int) -> VoiceState:
        if guild_id in self.voice_states:
            return self.voice_states.pop(guild_id)