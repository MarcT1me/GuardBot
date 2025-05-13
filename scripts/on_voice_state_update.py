import datetime

import discord
from loguru import logger

from bot import GuardBot, GuardDatabase


async def get_embed(bot: GuardBot, server: GuardDatabase.server, member: discord.Member,
                    template_name: str,
                    **kwargs) -> discord.Embed | None:
    template = await bot.db.get_template(server, template_name)
    if not template:
        logger.warning(f"Template {template_name} not found")
        return None

    embed = discord.Embed(
        color=0x3498db,
        timestamp=datetime.datetime.now()
    )

    parts = template.content.split("\\")
    for i, part in enumerate(parts):
        part = part.format(member=member, **kwargs)
        if i == 0:
            embed.title = part
        elif i == 1:
            embed.description = part
        elif i == 2:
            embed.set_footer(text=part, icon_url=member.avatar.url)

    embed.set_thumbnail(url=member.avatar.url)
    return embed


class Option:
    name: str = "nickname"
    change_allows: str = "nobody"
    size: str = "none"


async def main(*, bot: GuardBot, member: discord.Member,
               before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild
    server = await bot.db.get_server(guild.id)

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
                parent_channel_id=parent_channel.id,
                owner_id=member.id
            )

            await member.move_to(temp_channel)

            resp_channel: discord.TextChannel = guild.get_channel(server.additions["voice_channel_announce"])
            if embed := await get_embed(
                    bot, server, member,
                    "voice_channel_create",
                    temp_channel=temp_channel,
                    author=member,
                    parent_channel=parent_channel,
                    option=Option()
            ):
                await resp_channel.send(embed=embed)
            else:
                await resp_channel.send(
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
                parent_channel = guild.get_channel(db_parent_channel.id)

                resp_channel: discord.TextChannel = guild.get_channel(server.additions["voice_channel_announce"])
                if embed := await get_embed(
                        bot, server, member,
                        "voice_channel_delete",
                        temp_channel=before.channel,
                        author=guild.get_member(db_channel.additions["owner_id"]),
                        parent_channel=parent_channel,
                        option=Option()
                ):
                    await resp_channel.send(embed=embed)
                else:
                    await resp_channel.send(
                        f"User {member.mention} has left temp channel: `{before.channel.name}`\n"
                        f"time: {datetime.datetime.now().ctime()} * id: {member.id}",
                        allowed_mentions=discord.AllowedMentions(users=False, roles=False)
                    )

                await before.channel.delete(
                    reason=f"{parent_channel.name} child auto-clearing"
                )
                await bot.db.delete_channel(
                    before.channel.id
                )
                logger.success("Temp voice deleted")
