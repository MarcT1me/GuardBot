from bot.script_env import *

import lib.voice_option as voice_option
# voice_option: Any = include("lib.voice_option", "voice_option")


async def get_embed(bot: Bot, member: discord.Member,
                    template_name: str,
                    **kwargs) -> discord.Embed | None:
    template = await bot.guild.db.get_template(template_name=template_name)
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


async def main(*, bot: Bot, member: discord.Member,
               before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild

    if after.channel:
        db_channel: Optional[ScriptDatabase.channel] = await bot.guild.db.get_channel_by_id(channel_id=after.channel.id)

        if db_channel and db_channel.type == "voice_factory":
            voice_settings = voice_option.VoiceSettings.from_dict(
                (await bot.guild.db.get_user(user_id=member.id)).additions["voice_settings"]
            )

            parent_channel: discord.VoiceChannel = after.channel

            temp_channel: discord.VoiceChannel = await guild.create_voice_channel(
                name=voice_settings.get_name(member),
                category=parent_channel.category,
                reason=f"{parent_channel.name} child auto-creating",
                user_limit=voice_settings.size
            )
            await member.move_to(temp_channel)

            await bot.guild.db.save_temp_channel(
                channel_id=temp_channel.id,
                parent_channel_id=parent_channel.id,
                owner_id=member.id
            )

            logger.success("Temp voice created")

            try:
                if resp_channel := guild.get_channel(bot.guild.db.server_addition("voice_channel_announce")):
                    if embed := await get_embed(
                            bot, member, "voice_channel_create",
                            temp_channel=temp_channel,
                            author=member,
                            parent_channel=parent_channel,
                            option=voice_settings
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
        db_channel: ScriptDatabase.channel | None = await bot.guild.db.get_channel_by_id(channel_id=before.channel.id)

        if db_channel and db_channel.type == "temp_voice":
            if len(before.channel.members) == 0:
                db_parent_channel: ScriptDatabase.channel = await bot.guild.db.get_channel_by_id(
                    channel_id=db_channel.additions["parent_channel_id"]
                )
                parent_channel: discord.VoiceChannel = guild.get_channel(db_parent_channel.id)

                await before.channel.delete(
                    reason=f"{parent_channel.name} child auto-clearing" if parent_channel else "clear tem voice"
                )
                await bot.guild.db.delete_channel(
                    channel_id=before.channel.id
                )
                logger.success("Temp voice deleted")

                try:
                    if resp_channel := guild.get_channel(bot.guild.db.server_addition("voice_channel_announce")):
                        if embed := await get_embed(
                                bot, member, "voice_channel_delete",
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
