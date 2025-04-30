import discord
from discord import app_commands
from discord.ext import commands


class FunCog(commands.Cog):
    @app_commands.command(name="ping", description="...")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")


async def setup(bot: commands.Bot):
    print(f"⚙️ ModerationCog loading")
    await bot.add_cog(FunCog(bot))
