from bot.script_env import *
import lib.voice_option as voice_option


class ServerCog(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        logger.success(f"Setup guild only cog -> {bot.guild.name}")

    def get_settings_view(self) -> ui.View:
        return SettingsView(self.bot)


class SettingsView(ui.View):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot
        logger.debug(f"bot.guild: {self.bot.guild.name}")

    @ui.button(label="audio channels")
    async def change(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_message(  # type: ignore
            "Configure changes",
            view=ChangeVoiceSettingsView(
                self.bot,
                await voice_option.VoiceSettings.get_from_user(self.bot, interaction.user),
            ),
            ephemeral=True
        )

    @ui.button(label="resset")
    async def resset(self, interaction: discord.Interaction, _: ui.Button):
        voice_options: voice_option.VoiceSettings = voice_option.VoiceSettings(
            voice_option.NameSettings.nickname,
            voice_option.ChangeAllow.me_only,
            0
        )
        await voice_options.save_to_user(self.bot, interaction.user)
        await interaction.response.send_message(  # type: ignore
            "Successfully resset settings!",
            ephemeral=True
        )


class ChangeVoiceSettingsView(ui.View):
    def __init__(self, bot: Bot, voice_options: voice_option.VoiceSettings):
        super().__init__()
        self.bot: Bot = bot
        self.voice_options: voice_option.VoiceSettings = voice_options
        logger.debug(f"bot.guild: {self.bot.guild.name}")

    @ui.select(
        cls=ui.Select,
        placeholder="Choose a name type",
        options=[
            discord.SelectOption(
                label="Nickname",
                value="nickname",
            ),
            discord.SelectOption(
                label="Custom",
                value="custom",
            ),
        ]
    )
    async def name_select(self, interaction: discord.Interaction, select: ui.Select):
        self.voice_options.set_name_type(select.values[0])
        await interaction.response.defer(thinking=False)  # type: ignore

    @ui.select(
        cls=ui.Select,
        placeholder="Choose a change allow permission",
        options=[
            discord.SelectOption(
                label="Nobody",
                value="nobody",
            ),
            discord.SelectOption(
                label="You only",
                value="me_only",
            ),
            discord.SelectOption(
                label="Everyone",
                value="everyone",
            ),
        ]
    )
    async def change_allow_select(self, interaction: discord.Interaction, select: ui.Select):
        self.voice_options.set_change_type(select.values[0])
        await interaction.response.defer(thinking=False)  # type: ignore

    @ui.button(label="submit")
    async def submit(self, interaction: discord.Interaction, _: ui.Button):
        if self.voice_options.name is voice_option.NameSettings.custom:
            await interaction.response.send_modal(  # type: ignore
                ChangeWithCustomNameModel(self.bot, self.voice_options)
            )
        else:
            await interaction.response.send_modal(  # type: ignore
                ChangeModel(self.bot, self.voice_options)
            )


class ChangeModel(ui.Modal, title="Change settings"):
    def __init__(self, bot: Bot, voice_options: voice_option.VoiceSettings):
        super().__init__()
        self.bot: Bot = bot
        self.voice_options: voice_options = voice_options

        self.size = ui.TextInput(
            label="Room size",
            placeholder="0 for unsetted",
            max_length=2,
            default=str(voice_options.size)
        )
        self.add_item(self.size)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        self.voice_options.size = int(self.size.value)
        await self.voice_options.save_to_user(self.bot, interaction.user)
        await interaction.response.send_message(  # type: ignore
            "Change commited!",
            ephemeral=True
        )


class ChangeWithCustomNameModel(ui.Modal, title="Change settings (custom name)"):
    def __init__(self, bot: Bot, voice_options: voice_option.VoiceSettings):
        super().__init__()
        self.bot: Bot = bot
        self.voice_options: voice_options = voice_options

        self.size = ui.TextInput(
            label="Room size",
            placeholder="0 for unsetted",
            max_length=2,
            default=str(voice_options.size)
        )
        self.add_item(self.size)

        self.custom_name = ui.TextInput(
            label="Custom name",
            min_length=0,
            max_length=100,
            default=str(voice_options.custom_name) if voice_options.custom_name else None,
        )
        self.add_item(self.custom_name)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        self.voice_options.custom_name = self.custom_name.value or self.voice_options.custom_name
        self.voice_options.size = int(self.size.value)
        await self.voice_options.save_to_user(self.bot, interaction.user)
        await interaction.response.send_message(  # type: ignore
            "Change commited!",
            ephemeral=True
        )


async def main(*, bot: Bot, guild: discord.Guild):
    logger.debug(f"On Ready: {bot.name}, {guild.name}")
    await bot.setup_guild_only_cog(
        ServerCog(bot)
    )
