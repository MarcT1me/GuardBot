from bot.script_env import *

import lib.template_init as template_init
import lib.voice_option as voice_option


async def add_users(bot: Bot, interaction: discord.Interaction):
    for user in interaction.guild.members:
        await bot.guild.db.save_user(
            user_id=user.id,
            voice_settings=voice_option.VoiceSettings(
                voice_option.NameSettings.nickname,
                voice_option.ChangeAllow.me_only,
                0
            ).to_dict()
        )
    await interaction.followup.send("Users added to DataBase", ephemeral=True)


async def main(*, bot: Bot, interaction: discord.Interaction, voice_factory_list: list[dict[str, int]] = None):
    await bot.guild.db.init(interaction.guild_id, is_active=True)

    await interaction.followup.send(f"Guild: {interaction.guild} added to DataBase", ephemeral=True)

    try:
        await add_users(bot, interaction)
    except Exception as e:
        await interaction.followup.send(f"Error adding users: {e}", ephemeral=True)
        logger.exception("Error adding users")

    try:
        if voice_factory_list:
            for voice_factory in voice_factory_list:
                await bot.guild.db.save_factory_channel(channel_id=voice_factory["factory_channel"])
                await bot.guild.db.save_server_addition("voice_channel_announce", voice_factory["announce_channel"])

                await interaction.followup.send(
                    f"Voice Factory {voice_factory} added to GuardDatabase",
                    ephemeral=True
                )
    except Exception as e:
        await interaction.followup.send(
            f"Voice Factory adding error: {e}",
            ephemeral=True
        )
        logger.exception("Voice Factory adding error")

    try:
        await template_init.init(bot)
        await interaction.followup.send(
            "Template added to GuardDatabase",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"Error adding templates: {e}",
            ephemeral=True
        )
        logger.exception("Error adding templates")

    logger.success(f"init bot deps for {interaction.guild}")
