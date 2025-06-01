from bot.script_env import *

__all__ = "NameSettings", "ChangeAllow", "VoiceSettings"


class NameSettings(Enum):
    nickname = auto()
    custom = auto()


class ChangeAllow(Enum):
    nobody = auto()
    me_only = auto()
    everyone = auto()


class VoiceSettings:
    def __init__(
            self,
            name: NameSettings,
            change_allows: ChangeAllow,
            size: int,
            custom_name: Optional[str] = None
    ):
        self.name: NameSettings = name
        self.custom_name: Optional[str] = custom_name
        self.change_allows: ChangeAllow = change_allows
        self.size: int = size

    def set_name_type(self, type_name: str):
        self.name = getattr(NameSettings, type_name)

    def set_change_type(self, type_name: str):
        self.change_allows = getattr(ChangeAllow, type_name)

    def get_name(self, member: discord.Member):
        name_option = self.name

        if name_option == NameSettings.custom and self.custom_name:
            return self.custom_name

        return f"⏳ {member.name}\'s room"

    def to_dict(self):
        return {
            "name": self.name.name,
            "custom_name": self.custom_name,
            "change_allows": self.change_allows.name,
            "size": self.size
        }

    @classmethod
    def from_dict(cls, settings: dict):
        return cls(
            getattr(NameSettings, settings["name"]),
            getattr(ChangeAllow, settings["change_allows"]),
            settings["size"],
            custom_name=settings["custom_name"]
        )

    @classmethod
    async def get_from_user(cls, bot: Bot, member: discord.Member) -> 'VoiceSettings':
        user = await bot.guild.db.get_user(user_id=member.id)
        logger.debug(f"get_from_user: {bot.guild.id}")
        logger.debug(f"get_from_user: {member}")
        logger.debug(f"get_from_user: {user.additions}")
        if not user.additions:
            settings = cls(
                NameSettings.nickname,
                ChangeAllow.me_only,
                0
            )
            user.additions["voice_settings"] = settings.to_dict()
            return settings
        return cls.from_dict(
            user.additions["voice_settings"]
        )

    async def save_to_user(self, bot: Bot, member: discord.Member):
        db_user: ScriptDatabase.user = await bot.guild.db.get_user(user_id=member.id)
        db_user.additions["voice_settings"] = self.to_dict()
        await db_user.save()
