import os
import time
from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from openai import OpenAI

from bot.bot import GuardBot


class AiNames(Enum):
    Grok2 = "grok-2"
    Grok3Mini = "grok-3-mini"
    Grok3 = "grok-3"


class AiCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.manager = SessionManager(bot)

    @app_commands.command(name="change_ai_model", description="Switch AI model")
    @GuardBot.error_handler()
    async def change_ai_model(self, interaction: discord.Interaction, ai_model: str):
        self.manager.session(interaction.user).model_name = ai_model
        await interaction.response.send_message(f"Модель изменена на: `{ai_model}`", ephemeral=True)  # type: ignore

    @change_ai_model.autocomplete('ai_model')
    async def ai_model_autocomplete(
            self,
            _: discord.Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=model.value, value=model.value)
            for model in AiNames
            if all(c in model.value.lower() for c in current.lower())
        ]

    @app_commands.command(name="clear_ai_history", description="Clear AI chat history")
    @GuardBot.error_handler()
    async def clear_ai_history(self, interaction: discord.Interaction):
        self.manager.delete_session(interaction.user)
        await interaction.response.send_message("История чата очищена.", ephemeral=True)  # type: ignore

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        if self.bot.user.mentioned_in(msg):
            session = self.manager.session(msg.author)
            clean_content = msg.content.replace(f"<@{self.bot.user.id}>", "GuardBot").strip()
            await session.handle_message(msg, clean_content)


class ChatSession:
    XAI_API_KEY: str = os.getenv("XAI_API_KEY")
    MAX_HISTORY_LEN = 10
    UPDATE_INTERVAL = 0.1

    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.model_name: str = "grok-3-mini"
        self.history: list[dict[str, str]] = []

        self.system_prompt = {
            "role": "system",
            "content": (
                "Ты GuardBot, участник Discord-сервера. Отвечай кратко, по делу, дружелюбно. "
                "Адаптируйся к тону чата, избегай повторений и лишних слов."
            )
        }

    async def handle_message(self, message: discord.Message, user_input: str):
        client = OpenAI(api_key=self.XAI_API_KEY, base_url="https://api.x.ai/v1")

        self.history.append({"role": "user", "content": f"{message.author.name}:  {user_input}"})

        response_msg = await message.channel.send("GuardBot думает...")
        full_response = ""
        start_time = time.time()

        try:
            stream = client.chat.completions.create(
                model=self.model_name,
                messages=[self.system_prompt, *self.history],
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    if time.time() - start_time >= self.UPDATE_INTERVAL:
                        await response_msg.edit(content=full_response or "GuardBot думает...")

            self.history.append({"role": "assistant", "content": full_response})
            self._clean_history()

            embed = discord.Embed(title="Статистика", color=discord.Color.green())
            embed.add_field(name="Время", value=f"{time.time() - start_time:.2f} сек", inline=True)
            embed.add_field(name="Сообщений", value=f"{len(self.history) // 2}", inline=True)
            embed.add_field(name="Модель", value=self.model_name, inline=True)

            await response_msg.edit(content=full_response, embed=embed)

        except Exception as e:
            logger.error(f"AI error: {e}")
            await response_msg.edit(content=f"⚠️ Произошла ошибка при обработке запроса: {str(e)}")

            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()

    def _clean_history(self):
        if len(self.history) // 2 > self.MAX_HISTORY_LEN:
            self.history = self.history[-self.MAX_HISTORY_LEN * 2:]


class SessionManager:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.sessions: dict[int, ChatSession] = {}

    def session(self, user: discord.User) -> ChatSession:
        return self.sessions.setdefault(user.id, ChatSession(self.bot))

    def get_session(self, user: discord.User) -> ChatSession | None:
        return self.sessions.get(user.id)

    def delete_session(self, user: discord.User) -> ChatSession:
        return self.sessions.pop(user.id)


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ AiCog loading")
    await bot.add_cog(AiCog(bot))
