from bot.script_env import *

__all__ = "NameSettings", "ChangeAllow", "VoiceSettings"


class NameSettings(Enum):
    nickname = auto()
    status = auto()
    custom = auto()


class ChangeAllow(Enum):
    nobody = auto()
    me_only = auto()
    everyone = auto()


class VoiceSettings:
    def __init__(self, name: NameSettings, change_allows: ChangeAllow, size: int, custom_name: Optional[str] = None):
        self.name: NameSettings = name
        self.custom_name: Optional[str] = custom_name
        self.change_allows: ChangeAllow = change_allows
        self.size: int = size

    def get_name(self, member: discord.Member):
        name_option = self.name

        if name_option == NameSettings.status:
            for activity in member.activities:
                if isinstance(activity, discord.CustomActivity):
                    return activity.name
            else:
                name_option = NameSettings.custom

        if name_option == NameSettings.custom and self.custom_name:
            return self.custom_name

        return f"⏳ {member.name}\'s room"

    def to_dict(self):
        return {
            "name": self.name.name, "custom_name":
                self.custom_name, "change_allows":
                self.change_allows.name, "size": self.size
        }

    @classmethod
    def from_dict(cls, settings: dict):
        return cls(
            getattr(NameSettings, settings["name"]),
            getattr(ChangeAllow, settings["change_allows"]),
            settings["size"],
            custom_name=settings["custom_name"]
        )
