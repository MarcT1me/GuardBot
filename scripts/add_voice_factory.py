from bot.script_evs import *


async def main(*, bot: Bot, interaction: discord.Interaction, channel_id: int):
    await bot.guild.db.save_factory_channel(channel_id=channel_id)
    await interaction.channel.send("Voice Factory added to GuardDatabase")
