import datetime

import discord
from loguru import logger

from bot import GuardBot, GuardDatabase


async def main(*, bot: GuardBot, member: discord.Member,
               before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild

    if after.channel:
        db_channel: GuardDatabase.channel = await bot.db.get_channel_by_id(after.channel.id)

        if db_channel and db_channel.type == "voice_factory":
            parent_channel = after.channel

            temp_channel = await guild.create_voice_channel(
                name=f"{member.name}\'s room",
                category=parent_channel.category,
                reason=f"{parent_channel.name} child auto-creating"
            )

            await bot.db.save_temp_channel(
                server_id=guild.id,
                channel_id=temp_channel.id,
                name=temp_channel.id,
                parent_channel_id=parent_channel.id,
                owner_id=member.id
            )

            await member.move_to(temp_channel)

            server = await db_channel.server.get_or_none()
            voice_channel_announce: discord.TextChannel = guild.get_channel(
                server.additions["voice_channel_announce"]
            )

            await voice_channel_announce.send(
                f"User {member.mention} has create temp channel: {temp_channel.mention}\n"
                f"time: {datetime.datetime.now().ctime()} * id: {member.id}",
                allowed_mentions=discord.AllowedMentions(users=False, roles=False)
            )

            logger.success("Temp voice created")

    if before.channel:
        db_channel: GuardDatabase.channel = await bot.db.get_channel_by_id(before.channel.id)

        if db_channel and db_channel.type == "temp_voice":
            if len(before.channel.members) == 0:
                db_parent_channel: GuardDatabase.channel = await bot.db.get_channel_by_id(
                    db_channel.additions["parent_channel_id"]
                )

                await before.channel.delete(
                    reason=f"{db_parent_channel.name} child auto-clearing"
                )

                server = await db_channel.server.get_or_none()
                voice_channel_announce: discord.TextChannel = guild.get_channel(
                    server.additions["voice_channel_announce"]
                )

                await voice_channel_announce.send(
                    f"User {member.mention} has left temp channel: `{before.channel.name}`\n"
                    f"time: {datetime.datetime.now().ctime()} * id: {member.id}",
                    allowed_mentions=discord.AllowedMentions(users=False, roles=False)
                )

                await bot.db.delete_channel(before.channel.id)

                logger.success("Temp voice deleted")
