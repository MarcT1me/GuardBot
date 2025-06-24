from bot.script_env import *

import lib.template_init as template_init
import lib.voice_option as voice_option


async def add_users(bot: Bot, guild: discord.Guild, channel: discord.TextChannel) -> None:
    for user in guild.members:
        await bot.guild.db.save_user(
            user_id=user.id,
            voice_settings=voice_option.VoiceSettings(
                voice_option.NameSettings.nickname,
                voice_option.ChangeAllow.me_only,
                0
            ).to_dict()
        )
    await channel.send("Users added to DataBase")


async def main(*, bot: Bot, guild: discord.Guild):
    await bot.guild.db.init(guild.id, is_active=True)

    channel: discord.TextChannel = guild.safety_alerts_channel or guild.system_channel
    await channel.send(f"Guild: {guild} added to DataBase")

    try:
        await add_users(bot, guild, channel)
    except Exception as e:
        await  channel.send(f"Error adding users: {e}")
        logger.exception("Error adding users")

    try:
        await template_init.init(bot)
        await channel.send(
            "Template added to GuardDatabase"
        )
    except Exception as e:
        await channel.send(
            f"Error adding templates: {e}"
        )
        logger.exception("Error adding templates")

    logger.success(f"init bot deps for {guild}")
