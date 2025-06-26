from bot.script_env import *


async def main(*, bot: Bot, member: discord.Member = None, member_id: int = None, **kwargs):
    if member_id is not None:
        for member in bot.guild.members:
            if member.id == member_id:
                break

    if member.bot: return

    guild = member.guild

    if system_channel := guild.system_channel:
        try:
            greetings_list_template: ScriptDatabase.template = await bot.guild.db.get_template(
                template_name="greetings_list"
            )
            greetings = random.choice(greetings_list_template.content.split("\\"))
            await system_channel.send(
                greetings.format(member=member)
            )
        except Exception as e:
            await system_channel.send(
                f"У меня не получилось обработать приветствие с {member.mention}"
            )
            logger.exception(f"User greeting error: {e}")

    event = asyncio.Event()
    name = f"on_member_registered_{member.id}"
    bot.guild.set_async_event(name, event)
    logger.info(name + " " + str(event))

    try:
        await asyncio.wait_for(event.wait(), timeout=600)
    except asyncio.TimeoutError:
        # await guild.kick(member, reason="reg timeout")
        await member.send(
            "RU:\n"
            "Вы не согласились с ролями в течении 10 минут (БЕТА)\n"
            "Просим извинить если это ложное срабатывание. Если по какой-то причине вас удалило с сервера"
            "попытайтесь связаться с администрацией сервера.\n"
            "\n"
            "Eng:\n"
            "You didn't accept the rules within 10 minutes (BETA)\n"
            "Please excuse me if this is a false alarm. If for some reason you have been removed from the server, "
            "try to contact the server administration.\n"
            "\n"
            "P.S. for more information write - @mt_proger"
        )

    try:
        await bot.guild.db.save_user(
            user_id=member.id
        )
        logger.success(f"User {member.name} added to DataBase")
    except Exception as e:
        logger.exception(f"User saving error: {e}")

    try:
        title: ScriptDatabase.template = await bot.guild.db.get_template(template_name="join_message_title")
        description: ScriptDatabase.template = await bot.guild.db.get_template(template_name="join_message_description")
        descriptions = description.content.format(member=member).split("\\")
        footer: ScriptDatabase.template = await bot.guild.db.get_template(template_name="join_message_footer")

        embed = discord.Embed(
            title=title.content.format(member=member),
            description="",
            color=0xDE7A22
        )
        embed.add_field(
            name="RU",
            value=descriptions[0]
        )
        embed.add_field(
            name="Eng",
            value=descriptions[1]
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
