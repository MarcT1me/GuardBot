from bot.script_evs import *


async def main(*, bot: GuardBot, member: discord.Member = None, member_id: int = None, **kwargs):
    if member_id is not None:
        guild = bot.get_guild(guild_id)
        for member in guild.members:
            if member.id == member_id:
                break

    if member.bot: return

    guild = member.guild
    server: bot.db.server = await bot.db.get_server(guild_id=guild_id)

    if system_channel := guild.system_channel:
        try:
            greetings_list_template: bot.db.template = await bot.db.get_template(
                server=server,
                template_name="greetings_list"
            )
            greetings = random.choice(greetings_list_template.content.split("\\"))
            await system_channel.send(
                greetings.format(member=member)
            )
        except Exception as e:
            await system_channel.send(
                f"У меня не получилось обработать прощание с {member.mention}"
            )
            logger.exception(f"User greeting error: {e}")

    event = asyncio.Event()
    async_events[f"on_member_{member_id}"] = event

    try:
        await asyncio.wait_for(event.wait(), timeout=600)
    except asyncio.TimeoutError:
        await guild.kick(member, reason="reg timeout")
        return await member.send(
            "You didn't accept the rules within 10 minutes"
        )

    try:
        await bot.db.save_user(
            guild_id=member.guild.id,
            user_id=member.id
        )
        logger.success(f"User {member.name} added to DataBase")
    except Exception as e:
        logger.exception(f"User saving error: {e}")

    try:
        title: bot.db.template = await bot.db.get_template(server=server, template_name="join_message_title")
        description: bot.db.template = await bot.db.get_template(server=server,
                                                                 template_name="join_message_description")
        footer: bot.db.template = await bot.db.get_template(server=server, template_name="join_message_footer")

        embed = discord.Embed(
            title=title.content.format(member=member),
            description=description.content.format(member=member),
            color=0xDE7A22
        )
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=footer.content.format(member=member), icon_url=member.avatar.url)

        img_name: str = "welcome_ByPROtoKOPs.png"
        embed.set_image(url=f"attachment://{img_name}")
        await member.send(
            embed=embed,
            file=discord.File("assets/welcome_ByPROtoKOPs.png", filename=img_name)
        )
    except Exception as e:
        logger.exception(f"User dm greeting sending error: {e}")
