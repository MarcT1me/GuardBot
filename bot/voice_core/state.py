import asyncio
from typing import Optional

import discord

from loguru import logger

from bot import GuardBot
from .track import BaseTrack, TrackSource


class VoiceState:
    def __init__(self):
        self._voice_client: Optional[discord.VoiceClient] = None
        self._current_channel: Optional[discord.VoiceChannel | discord.StageChannel] = None

        self.current_track: Optional[BaseTrack] = None
        self.queue: list[BaseTrack] = []

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

    async def add_source(self, track: BaseTrack, index: int = None) -> None:
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
