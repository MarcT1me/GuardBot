import asyncio
from typing import Optional, Iterator
import time

import discord
from loguru import logger

from bot import GuardBot
from .track import BaseTrack, TrackFile, TrackStream


class VoiceState:
    def __init__(self):
        self._voice_client: Optional[discord.VoiceClient] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

        self.current_track: Optional[BaseTrack] = None
        self.queue: list[BaseTrack] = []

        self._is_active = False
        self._is_restart = False
        self.restart_count = 0

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
    def is_active(self) -> bool:
        return self._is_active

    @property
    def current_channel(self) -> discord.VoiceChannel | discord.StageChannel | None:
        return self._current_channel

    async def iter_queue(self) -> Iterator[tuple[int, BaseTrack]]:
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
                await self.stop()

            await self._voice_client.disconnect()
            logger.info(f"Disconnecting from {self._current_channel.name}")

            self._voice_client = None
            self._current_channel = None

    async def play(self, track: BaseTrack, interaction: discord.Interaction) -> None:
        if self._voice_client:
            if isinstance(track, TrackFile):
                return self._voice_client.play(track.source)
            await self.add_source(track, index=0)
            await self.play_next(interaction)
        return None

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

            self._is_restart = False

            # Ожидаем завершения текущего трека
            while self.is_playing or self.is_paused:
                await asyncio.sleep(0.0)

            if self.queue:
                await interaction.channel.send(
                    f"Switching to the next track **{self.queue[0].beautiful_title}**"
                )

        if not self.queue and self._is_active:
            await interaction.channel.send("The playback queue has ended")

        self._is_active = False

    async def _set_next(self):
        if self.current_track:
            await self.stop()

        if self.queue:
            next_track = self.queue.pop(0)
            await next_track.create_source() if not self._is_restart else None
            self.current_track = next_track
            logger.info(f"set next track: {next_track.beautiful_title}")

    async def _play_current(self, interaction):
        if not self._voice_client or not self.current_track:
            return

        self.current_track.playback_start = time.time()
        self.current_track.paused_duration = 0.0
        self.current_track.last_pause_time = None

        self._voice_client.play(
            self.current_track.source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self._handle_playback(e, interaction),
                self._voice_client.loop
            )
        )
        logger.info(f"play track, {self.current_track.beautiful_title}")

    async def _handle_playback(
            self, error: Optional[Exception], interaction: discord.Interaction
    ) -> discord.Message | None:
        if error:
            logger.error(f"Playback error: {str(error)}")
            return await interaction.followup.send(f"Playback error: {str(error)}", ephemeral=True)

        # elapsed = await self.calculate_playback_time()
        #
        # if elapsed < self.current_track.duration - 2 and self._is_active:
        #     if self.restart_count < 10:
        #         await self._restart_track(elapsed)
        #         self.restart_count += 1
        #     else:
        #         self.restart_count = 0
        # else:
        #     self.restart_count = 0

        if self.current_track:
            self.current_track.cleanup()
            self.current_track = None
        return None

    async def calculate_playback_time(self) -> float:
        if not self.current_track or not self.current_track.playback_start:
            return 0.0

        total_time = time.time() - self.current_track.playback_start + self.current_track.start_pos
        paused_time = self.current_track.paused_duration

        if self.current_track.last_pause_time:
            paused_time += time.time() - self.current_track.last_pause_time

        return total_time - paused_time

    async def seek(self, position: float, interaction: discord.Interaction) -> None:
        """Перемотка текущего трека"""
        if not self.current_track:
            return

        if position < 0:
            position = 0
        if position > self.current_track.duration:
            position = self.current_track.duration - 1

        # Останавливаем и перезапускаем с новой позиции
        if self._voice_client and (self.is_playing or self.is_paused):
            await self._restart_track(position)

    async def _restart_track(self, position: float):
        logger.warning(f"Restarting track from {position}s: {self.current_track.beautiful_title}")
        self._is_restart = True

        new_track = TrackStream( self.current_track.url, info=self.current_track.info)
        await new_track.create_source(start_time=position)

        self.queue.insert(0, new_track)

        is_active = self._is_active
        await self.stop()
        self._is_active = is_active

    async def pause(self) -> None:
        if self.is_playing and self.current_track:
            self.current_track.last_pause_time = time.time()
            logger.info(f"pause track, {self.current_track.beautiful_title}")
            self._voice_client.pause()

    async def resume(self) -> None:
        if self.is_paused and self.current_track:
            if self.current_track.last_pause_time:
                self.current_track.paused_duration += time.time() - self.current_track.last_pause_time
                self.current_track.last_pause_time = None
            logger.info(f"resume track, {self.current_track.beautiful_title}")
            self._voice_client.resume()

    async def stop(self) -> None:
        self._is_active = False

        if self.is_playing:
            self._voice_client.stop()

        if self.current_track:
            logger.info(f"stop track, {self.current_track.beautiful_title}")
            await self.cleanup_current()

    async def cleanup(self) -> None:
        self._is_active = False

        await self.cleanup_current()

        await self.cleanup_queue()

    async def cleanup_current(self) -> None:
        if self.current_track:
            self.current_track.cleanup()
            self.current_track = None

    async def cleanup_queue(self) -> None:
        for i in range(len(self.queue)):
            self.queue.pop().cleanup()


class VoiceStateManager:
    def __init__(self):
        self.voice_states: dict[int, VoiceState] = {}

    async def disconnect_all(self):
        for guild in GuardBot.instance.guilds:
            await self.disconnect_guild(guild)

    async def disconnect_guild(self, guild: discord.Guild):
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

    def remove(self, guild_id: int) -> VoiceState | None:
        if guild_id in self.voice_states:
            return self.voice_states.pop(guild_id)
        return None
