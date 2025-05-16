from bot.script_evs import *


async def main(*, bot: GuardBot, member: discord.Member):
    if member.bot: return

    try:
        await bot.db.remove_user(server=await bot.db.get_server(guild_id=guild_id), user_id=member.id)
        logger.success(f"User {member.name} removed from DataBase")
    except Exception as e:
        logger.exception(f"User removing error: {e}")

    guild = bot.get_guild(guild_id)
    server: bot.db.server = await bot.db.get_server(guild_id=guild_id)

    if system_channel := guild.system_channel:
        try:
            farewell_list_template = await bot.db.get_template(
                server=server,
                template_name="farewell_list"
            )
            farewell = random.choice(farewell_list_template.content.split("\\"))
            await system_channel.send(
                farewell.format(member=member)
            )
        except Exception as e:
            await system_channel.send(
                f"{member.mention} вышел с сервера"
            )
            logger.exception(f"User farewell error: {e}")
