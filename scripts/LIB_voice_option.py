from bot.script_evs import *


class NameSettings(Enum):
    nickname = auto()
    status = auto()
    custom = auto()


class ChangeAllow(Enum):
    nobody = auto()
    me_only = auto()
    everyone = auto()


class VoiceSettings:
    def __init__(self, name: NameSettings, change_allows: ChangeAllow, size: int):
        self.name: NameSettings = name
        self.change_allows: ChangeAllow = change_allows
        self.size: int = size

    def to_dict(self):
        return {"name": self.name.name, "change_allows": self.change_allows.name, "size": self.size}

    @classmethod
    def from_dict(cls, d):
        return cls(
            getattr(NameSettings, d["name"]),
            getattr(ChangeAllow, d["change_allows"]),
            d["size"]
        )
