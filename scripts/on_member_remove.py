from bot.script_env import *


async def main(*, bot: Bot, member: discord.Member):
    if member.bot: return

    guild = member.guild

    try:
        await bot.guild.db.remove_user(user_id=member.id)
        logger.success(f"User {member.name} removed from DataBase")
    except Exception as e:
        logger.exception(f"User removing error: {e}")

    if system_channel := guild.system_channel:
        try:
            farewell_list_template = await bot.guild.db.get_template(
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
