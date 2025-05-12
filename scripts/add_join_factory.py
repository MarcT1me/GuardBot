import discord

from bot import GuardBot


async def main(*, bot: GuardBot, interaction: discord.Interaction, channel_id: int, chanel_name: str):
    await bot.db.save_factory_channel(
        interaction.guild.id,
        channel_id,
        chanel_name
    )

    await interaction.channel.send("GuardDatabase updated")
