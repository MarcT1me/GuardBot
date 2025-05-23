import datetime

import discord
from loguru import logger

from bot import GuardBot


class ExecutorSeance:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.env: dict = {}
        self.clear_env()

    def expand_env(self, **context) -> dict:
        self.env.update(**context)
        return self.env

    def clear_env(self) -> None:
        self.env = {
            "response": self.response,
            "flush_response": self.flush_response,
            "__std_send_response_message__": ""
        }

    def response(self, *args, sep: str = " ", end: str = "\n") -> None:
        self.env["__std_send_response_message__"] += sep.join([str(arg) for arg in args]) + end

    def clear_response(self) -> None:
        self.env["__std_send_response_message__"] = ""

    async def flush_response(self) -> None:
        await self.env["send"](
            f"{datetime.datetime.now().ctime()} | ```\n{self.env["__std_send_response_message__"]}\n```"
        )
        self.clear_response()

    async def execute(self, lang: str, code: str, guild_id: int, **context) -> any:
        try:
            script, ret = await self.bot.script_eng.fast_execute(lang, code, guild_id, self.env, **context)
            self.expand_env(**script.code_env)

            self.clear_response()
            return ret
        except Exception as e:
            logger.exception(f"{e}")
            return e
        except RuntimeWarning as e:
            logger.exception(f"{e}")
            return e


class ExecutorManager:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.seances: dict[int, ExecutorSeance] = {}

    def get_seance(self, user: discord.User) -> ExecutorSeance | None:
        return self.seances.get(user.id)

    def seance(self, user: discord.User):
        if user.id in self.seances:
            return self.get_seance(user)
        return self.create_seance(user)

    def create_seance(self, user: discord.User) -> ExecutorSeance:
        seance = ExecutorSeance(self.bot)
        self.seances[user.id] = seance
        return seance

    def delete_seance(self, user: discord.User) -> ExecutorSeance:
        return self.seances.pop(user.id)
