import discord

from bot import GuardBot


async def main(*, bot: GuardBot, interaction: discord.Interaction):
    await bot.db.save_botdevuser(
        805395077496832011,
        "marc_time",
    )
    await bot.db.save_botdevuser(
        864811730337267734,
        "just4763",
    )
    await bot.db.save_botdevuser(
        1226073097136771135,
        "_.snaik._",
    )

    await interaction.channel.send("GuardDatabase updated")
