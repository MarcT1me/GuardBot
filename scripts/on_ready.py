from bot.script_evs import *


class EliteGuardionCog(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        logger.success(f"Setup guild only cog -> {bot.guild.name}")

    @app_commands.command(name="test_cmd", description="command only for Elite: Guardian")
    @app_commands.describe(member="test member for output")
    async def test_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.channel.send(
            f"ХУЙ, {member.mention}",
            allowed_mentions=discord.AllowedMentions(users=False)
        )


async def main(*, bot: Bot, guild: discord.Guild):
    # await guild.system_channel.send(f"On Ready: {bot.user.name}, {guild.name}")
    logger.debug(f"On Ready: {bot.name}, {guild.name}")
    # if guild.id == 957269545326891028:
    #     await bot.setup_guild_only_cog(
    #         EliteGuardionCog(bot)
    #     )
