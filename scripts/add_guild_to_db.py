from bot.script_env import *

import lib.template_init as template_init
import lib.voice_option as voice_option


async def add_users(bot: Bot, interaction: discord.Interaction):
    for user in interaction.guild.members:
        await bot.guild.db.save_user(
            user_id=user.id,
            voice_settings=voice_option.VoiceSettings(
                voice_option.NameSettings.nickname,
                voice_option.ChangeAllow.nobody,
                0
            ).to_dict()
        )
    await interaction.channel.send("Users added to DataBase")


async def main(*, bot: Bot, interaction: discord.Interaction):
    await bot.guild.db.init(interaction.guild_id, is_active=True)

    await interaction.channel.send(f"Guild: {interaction.guild} added to DataBase")

    try:
        await add_users(bot, interaction)
    except Exception as e:
        await interaction.channel.send(f"Error adding users: {e}")
        logger.exception("Error adding users")

    try:
        if interaction.guild.id == 957269545326891028:
            await bot.guild.db.save_factory_channel(channel_id=1371185726502338610)
            await bot.guild.db.save_server_addition("voice_channel_announce", 1371207588045262868)

            await interaction.channel.send("Voice Factory added to GuardDatabase")
    except Exception as e:
        await interaction.channel.send(f"Voice Factory adding error: {e}")
        logger.exception("Voice Factory adding error")

    try:
        await template_init.init(bot)
        await interaction.channel.send("Template added to GuardDatabase")
    except Exception as e:
        await interaction.channel.send(f"Error adding templates: {e}")
        logger.exception("Error adding templates")

    logger.success(f"init bot deps for {interaction.guild}")
