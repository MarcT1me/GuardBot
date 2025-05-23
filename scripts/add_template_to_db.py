from bot.script_env import *

import lib.template_init as template_init


async def main(*, bot: Bot, interaction: discord.Interaction):
    await template_init.init(bot)
    await interaction.followup.send("Templates added to DataBase", ephemeral=True)
