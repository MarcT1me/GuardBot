from bot.script_evs import *


class EliteGuardionCog(Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot

        logger.success("Setup guild only cog")

    @app_commands.command(name="test_cmd", description="command only for EliteGuardion")
    @app_commands.describe(member="test member for output")
    async def test_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.channel.send(
            f"ХУЙ, {member.mention}",
            allowed_mentions=discord.AllowedMentions(users=False)
        )


async def main(*, bot: GuardBot, guild: discord.Guild):
    # await guild.system_channel.send(f"On Ready: {bot.user.name}, {guild.name}")
    logger.debug(f"On Ready: {bot.user.name}, {guild.name}")
    if guild_id == 957269545326891028:
        if "EliteGuardionCog" in bot.cogs:
            await bot.remove_cog("EliteGuardionCog", guild=guild)
        await bot.add_cog(EliteGuardionCog(bot), override=True, guild=guild)
        await bot.tree.sync(guild=guild)
