from bot.script_env import *
import lib.voice_option as voice_option


class ServerCog(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        logger.success(f"Setup guild only cog -> {bot.guild.name}")

    def get_settings_view(self, interaction: discord.Interaction) -> ui.View:
        return SettingsView(self.bot, interaction)


class SettingsView(ui.View):
    def __init__(self, bot: Bot, interaction: discord.Interaction):
        super().__init__()
        self.bot: Bot = bot
        logger.debug(f"bot.guild: {self.bot.guild.name}")

        if interaction.user.guild_permissions.administrator:
            btn = ui.Button(label="Admin")
            btn.callback = self.admin_settings
            self.add_item(btn)

    async def admin_settings(self, interaction: discord.Interaction):
        await interaction.response.send_message(  # type: ignore
            "Admin Settings pannel",
            view=AdminSettingsView(
                self.bot,
                interaction,
            ),
            ephemeral=True
        )

    @ui.button(label="audio channels")
    async def audio_change(self, interaction: discord.Interaction, _: ui.Button):
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


class AdminSettingsView(ui.View):
    def __init__(self, bot: Bot, interaction: discord.Interaction):
        super().__init__()
        self.bot: Bot = bot
        self.interaction: discord.Interaction = interaction

    @ui.button(label="Add voice factory")
    async def add_voice_factory(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            AddVoiceFactoryModel(self.bot)
        )

    @ui.button(label="Remove voice factory")
    async def rem_voice_factory(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.send_modal(  # type: ignore
            RemVoiceFactoryModel(self.bot)
        )

    @ui.button(label="Display voice factory")
    async def display_voice_factory(self, interaction: discord.Interaction, _: ui.Button):
        resp = "Channel factories:\n```\n"
        for channel in await self.bot.guild.db.get_channels(channel_type="voice_factory"):
            resp += f"{channel.id}: {channel.additions}\n"
        resp += "```\n"
        resp += f"Announce channel:\n```\n{self.bot.guild.db.server_addition("voice_channel_announce")}```\n"
        await interaction.response.send_message(resp, ephemeral=True)  # type: ignore

    @ui.button(label="Change AI System prompt")
    async def change_ai_system_prompt(self, interaction: discord.Interaction, _: ui.Button):
        default = await self.bot.guild.db.get_template(template_name="ai_system_prompt")
        await interaction.response.send_modal(  # type: ignore
            ChangeSystemPrompt(self.bot, default.content)
        )


class AddVoiceFactoryModel(ui.Modal, title="Add voice factory"):
    channel_id = ui.TextInput(
        label="factory channel id",
        placeholder="1371111444402333333 for example",
    )
    cooldown = ui.TextInput(
        label="channel cooldown",
        default="5.5"
    )
    is_active = ui.TextInput(
        label="is active",
        default="True"
    )

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

        self.announce_channel = ui.TextInput(
            label="announce channel id",
            placeholder="1371111444402333333 for example",
            default=self.bot.guild.db.server_addition("voice_channel_announce")
        )
        self.add_item(self.announce_channel)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        logger.debug("try save")
        await self.bot.guild.db.save_factory_channel(
            channel_id=int(self.channel_id.value),
            cooldown=float(self.cooldown.value),
            is_active=self.is_active.value == "True",
        )
        await self.bot.guild.db.save_server_addition(
            "voice_channel_announce", self.announce_channel.value
        )
        await interaction.response.send_message("successfully add factory", ephemeral=True)  # type: ignore


class RemVoiceFactoryModel(ui.Modal, title="Add voice factory"):
    channel_id = ui.TextInput(
        label="factory channel id",
        placeholder="1371111444402333333 for example",
    )

    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        await self.bot.guild.db.delete_channel(channel_id=int(self.channel_id))


class ChangeSystemPrompt(ui.Modal, title="Change System prompt"):
    def __init__(self, bot: Bot, default: str):
        super().__init__()
        self.bot: Bot = bot

        self.template = ui.TextInput(
            label="template",
            default=default,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.template)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        await self.bot.guild.db.save_template(
            name="ai_system_prompt",
            content=self.template.value or
                    "Ты GuardBot, участник Discord-сервера. Отвечай кратко, по делу, дружелюбно. "
                    "Адаптируйся к тону чата, избегай повторений и лишних слов."
        )
        await interaction.response.send_message("Successfully changed system prompt", ephemeral=True)  # type: ignore


async def main(*, bot: Bot, guild: discord.Guild):
    logger.debug(f"On Ready: {bot.name}, {guild.name}")
    await bot.setup_guild_only_cog(
        ServerCog(bot)
    )
