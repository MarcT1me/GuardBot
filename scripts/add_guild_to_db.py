from bot.script_evs import *


async def add_users(bot: GuardBot, interaction: discord.Interaction):
    for user in interaction.guild.members:
        server = await bot.db.get_server(interaction.guild_id)
        db_user = await bot.db.get_user(server=server, user_id=user.id)

        if db_user: continue

        await bot.db.save_user(
            interaction.guild_id,
            user.id,
            user.name,
            ""
        )
    await interaction.channel.send("Users added to DataBase")

    await bot.script_eng.execute("add_bot_dev_users", None, interaction=interaction)


async def main(*, bot: GuardBot, interaction: discord.Interaction):
    kwargs = {
        "is_active": True
    }

    server = await bot.db.save_server(
        interaction.guild.id,
        interaction.guild.name,
        **kwargs
    )

    await interaction.channel.send(f"Guild: {interaction.guild} added to DataBase")

    try:
        await add_users(bot, interaction)
    except Exception as e:
        await interaction.channel.send(f"Error adding users: {e}")
        logger.exception("Error adding users")

    try:
        if interaction.guild.id == 957269545326891028:
            await bot.script_eng.execute(
                "add_voice_factory", None,
                interaction=interaction,
                channel_id=1371185726502338610
            )
            server.additions["voice_channel_announce"] = 1371207588045262868
            await server.save()
    except Exception as e:
        await interaction.channel.send(f"Voice Factory adding error: {e}")
        logger.exception("Voice Factory adding error")

    try:
        await bot.script_eng.execute("add_template_to_db", None, interaction=interaction)
    except Exception as e:
        await interaction.channel.send(f"Error adding templates: {e}")
        logger.exception("Error adding templates")

    logger.success(f"init bot deps for {interaction.guild}")
