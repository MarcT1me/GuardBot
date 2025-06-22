from bot.script_env import *

import lib.voice_option as voice_option


async def get_embed(bot: Bot, member: discord.Member,
                    template_name: str,
                    author: discord.Member,
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
        part = part.format(member=member, author=author, **kwargs)
        if i == 0:
            embed.title = part
        elif i == 1:
            embed.description = part
        elif i == 2:
            embed.set_footer(text=part, icon_url=author.avatar.url)

    embed.set_thumbnail(url=member.avatar.url)
    return embed


async def get_temp_channel(
        guild: discord.Guild, member: discord.Member,
        voice_settings: voice_option.VoiceSettings,
        parent_channel: discord.VoiceChannel,
        db_channel: ScriptDatabase.channel
) -> discord.VoiceChannel:
    cur_time = datetime.datetime.now().timestamp()
    if (
            cur_time + db_channel.additions["last_creating_time"] >= db_channel.additions["cooldown"]
            or not db_channel.additions["last_created_channel"]
    ):
        return await guild.create_voice_channel(
            name=voice_settings.get_name(member),
            category=parent_channel.category,
            reason=f"{parent_channel.name} child auto-creating",
            user_limit=voice_settings.size,
            position=parent_channel.position
        )
    else:
        return guild.get_channel(db_channel.additions["last_created_channel"])


# noinspection PyUnresolvedReferences,PyDunderSlots
async def main(*, bot: Bot, member: discord.Member,
               before: discord.VoiceState, after: discord.VoiceState):
    guild: discord.Guild = member.guild

    if after.channel:
        db_channel: Optional[ScriptDatabase.channel] = await bot.guild.db.get_channel_by_id(channel_id=after.channel.id)

        if db_channel and db_channel.type == "voice_factory" and db_channel.additions["is_active"]:
            voice_settings: voice_option.VoiceSettings = await voice_option.VoiceSettings.get_from_user(bot, member)

            parent_channel: discord.VoiceChannel = after.channel

            temp_channel: discord.VoiceChannel = get_temp_channel(guild, member, voice_settings, parent_channel, db_channel)
            await member.move_to(temp_channel)
            db_channel.additions["last_creating_time"] = cur_time
            db_channel.additions["last_created_channel"] = temp.id
            db_channel.save()

            try:
                set_permission = voice_settings.change_allows != voice_option.ChangeAllow.nobody
                override_obj = member \
                    if voice_settings.change_allows == voice_option.ChangeAllow.me_only \
                    else guild.default_role
                member_permissions = temp_channel.overwrites_for(override_obj)
                member_permissions.manage_channels = set_permission
                member_permissions.move_members = set_permission
                member_permissions.mute_members = set_permission
                await temp_channel.set_permissions(
                    override_obj,
                    overwrite=member_permissions,
                    reason=f"{parent_channel.name} child auto-creating"
                )
                logger.success(f"Set permission in {temp_channel.name} for {member.name}")
            except Exception as e:
                logger.error(f"Can\'t set permission in {temp_channel.name} for {member.name}: {e}")

            await bot.guild.db.save_temp_channel(
                channel_id=temp_channel.id,
                parent_channel_id=parent_channel.id,
                owner_id=member.id
            )

            logger.success("Temp voice created")

            try:
                if resp_channel := guild.get_channel(bot.guild.db.server_addition("voice_channel_announce")):
                    if embed := await get_embed(
                            bot,
                            member,
                            "voice_channel_create",
                            member,
                            temp_channel=temp_channel,
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
        db_channel: Optional[ScriptDatabase.channel] = await bot.guild.db.get_channel_by_id(
            channel_id=before.channel.id)

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
                db_channel.additions["last_created_channel"] = None
                db_channel.save()

                logger.success("Temp voice deleted")

                try:
                    if resp_channel := guild.get_channel(bot.guild.db.server_addition("voice_channel_announce")):
                        if embed := await get_embed(
                                bot,
                                member,
                                "voice_channel_delete",
                                guild.get_member(db_channel.additions["owner_id"]),
                                temp_channel=before.channel,
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
