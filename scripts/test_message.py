from bot.script_env import *


async def main(*, bot: Bot, interaction: discord.Interaction):
    await interaction.followup.send(
        "Test message",
        ephemeral=True
    )
    return None
