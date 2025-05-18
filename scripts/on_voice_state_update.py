from bot.script_evs import *


async def get_embed(bot: GuardBot, server, member: discord.Member,
                    template_name: str,
                    **kwargs) -> discord.Embed | None:
    template = await bot.db.get_template(server=server, template_name=template_name)
    if not template:
        logger.warning(f"Template {template_name} not found")
        return None

    embed = discord.Embed(
        color=0x3498db,
        timestamp=datetime.datetime.now()
    )

    parts: list[str] = template.content.split("\\")
    for i, part in iterate(parts):
        part = part.format(member=member, **kwargs)
        if i == 0:
            embed.title = part
        elif i == 1:
            embed.description = part
        elif i == 2:
            embed.set_footer(text=part, icon_url=member.avatar.url)

    embed.set_thumbnail(url=member.avatar.url)
    return embed


async def main(*, bot: GuardBot, member: discord.Member,
               before: discord.VoiceState, after: discord.VoiceState):
    class Option:
        name: str = "nickname"
        change_allows: str = "nobody"
        size: str = "none"

    guild = member.guild
    server = await bot.db.get_server(guild_id=guild.id)

    if after.channel:
        db_channel: bot.db.channel | None = await bot.db.get_channel_by_id(channel_id=after.channel.id)

        if db_channel and db_channel.type == "voice_factory":
            parent_channel: discord.VoiceChannel = after.channel

            temp_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=f"⏳ {member.name}\'s room",
                category=parent_channel.category,
                reason=f"{parent_channel.name} child auto-creating"
            )
            await member.move_to(temp_channel)

            await bot.db.save_temp_channel(
                server_id=guild.id,
                channel_id=temp_channel.id,
                parent_channel_id=parent_channel.id,
                owner_id=member.id
            )

            logger.success("Temp voice created")

            try:
                if resp_channel := guild.get_channel(server.additions["voice_channel_announce"]):
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
            except Exception as e:
                logger.error(f"Can not send message: {e}")

    if before.channel:
        db_channel: bot.db.channel | None = await bot.db.get_channel_by_id(channel_id=before.channel.id)

        if db_channel and db_channel.type == "temp_voice":
            if len(before.channel.members) == 0:
                db_parent_channel: bot.db.channel = await bot.db.get_channel_by_id(
                    channel_id=db_channel.additions["parent_channel_id"]
                )
                parent_channel: discord.VoiceChannel = guild.get_channel(db_parent_channel.id)

                await before.channel.delete(
                    reason=f"{parent_channel.name} child auto-clearing" if parent_channel else "clear tem voice"
                )
                await bot.db.delete_channel(
                    channel_id=before.channel.id
                )
                logger.success("Temp voice deleted")

                try:
                    if resp_channel := guild.get_channel(server.additions["voice_channel_announce"]):
                        if embed := await get_embed(
                                bot, server, member,
                                "voice_channel_delete",
                                temp_channel=before.channel,
                                author=guild.get_member(db_channel.additions["owner_id"]),
                                parent_channel=parent_channel
                        ):
                            await resp_channel.send(embed=embed)
                        else:
                            await resp_channel.send(
                                f"User {member.mention} has left temp channel: `{before.channel.name}`\n"
                                f"time: {datetime.datetime.now().ctime()} * id: {member.id}",
                                allowed_mentions=discord.AllowedMentions(users=False, roles=False)
                            )
                except Exception as e:
                    logger.error(f"Can not send message: {e}")
