from bot.script_evs import *


async def main(*, bot: GuardBot, interaction: discord.Interaction, channel_id: int):
    await bot.db.save_factory_channel(
        server_id=interaction.guild.id,
        channel_id=channel_id
    )

    await interaction.channel.send("Voice Factory added to GuardDatabase")
