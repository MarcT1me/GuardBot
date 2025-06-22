import os
import time
from enum import Enum
from queue import Queue

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from openai import OpenAI

from bot.bot import GuardBot


class AiNames(str, Enum):
    Grok3 = "grok-3"
    Grok3Mini = "grok-3-mini"


class AiCog(commands.Cog):
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.manager = SessionManager(bot)

    @app_commands.command(name="change_ai_model", description="Check AI model")
    @GuardBot.error_handler()
    async def change_ai_model(self, interaction: discord.Interaction, ai_model: AiNames):
        # Получаем задержку в миллисекундах
        self.manager.session(interaction.user.id).model_name = ai_model.value
        await interaction.response.send_message(f"Выбрана модель: `{ai_model.name}`")  # type: ignore

    @change_ai_model.autocomplete('ai_model')
    async def ai_model_autocomplete(
            self,
            _: discord.Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        choices = []
        for model in AiNames:
            # Фильтрация по введённому тексту
            if current.lower() in model.value.lower():
                choices.append(
                    app_commands.Choice(
                        name=model.value,
                        value=model.value
                    )
                )
        return choices

    @app_commands.command(name="clear_ai_history", description="Check AI model")
    @GuardBot.error_handler()
    async def clear_ai_history(self, interaction: discord.Interaction):
        # Получаем задержку в миллисекундах
        self.manager.session(interaction.user.id).history = Queue(maxsize=5)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        if self.bot.user.mentioned_in(msg):
            session = self.manager.session(msg.author)

            clean_content = msg.content.replace(f"<@{self.bot.user.id}>", "GuardBot").strip()

            # Работаем с сообщением
            await session.handle_message(msg, clean_content)


class ChatSession:
    XAI_API_KEY: str = os.getenv("XAI_API_KEY")
    MAX_HISTORY_LEN = 5
    UPDATE_INTERVAL = 1.0

    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.model_name: str = "grok-3-mini"
        self.history: list[str] = []

        self.system_prompt = {
            "role": "system",
            "content": (
                "Ты GuardBot, ИИ-помощник в Discord. Твои характеристики:\n"
                "- Ты помогаешь пользователям отвечать на вопросы\n"
                "- Отвечай кратко и информативно\n"
                "- Ты общаешься в чате Discord сервера\n"
                "- Используй эмодзи для выразительности 🚀\n"
                "- Будь дружелюбным и полезным помощником"
            )
        }

    async def handle_message(self, message: discord.Message, user_input: str):
        client = OpenAI(
            api_key=self.XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )

        self.history.append({
            "role": "user",
            "content": user_input
        })

        response_msg = await message.channel.send("Подождите, GuardBot начал обработку вашего сообщения")
        full_response = ""
        is_first_chunk = True
        start_time = time.time()
        last_update = start_time
        model_name = self.model_name

        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=[self.system_prompt, *self.history],
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                    full_response += chunk_content

                    current_time = time.time()
                    if current_time - last_update >= self.UPDATE_INTERVAL or is_first_chunk:

                        if len(full_response) > 2000:
                            display_text = full_response[:1997] + "..."
                        else:
                            display_text = full_response

                        await response_msg.edit(content=display_text)

                        last_update = current_time
                        is_first_chunk = False

            self.history.append({
                "role": "assistant",
                "content": full_response
            })
            self._clean_history()

            end_time = time.time()
            duration = end_time - start_time

            embed = discord.Embed(
                title="Статистика запроса",
                color=discord.Color.green()
            )
            embed.add_field(name="Длительность", value=f"{duration:.2f} сек", inline=True)
            embed.add_field(name="Сообщений в истории", value=f"{len(self.history)}", inline=True)
            embed.add_field(name="Модель", value=model_name, inline=True)

            await response_msg.edit(content=full_response, embed=embed)

        except Exception as e:
            logger.error(f"AI error: {e}")
            await response_msg.edit(content=f"⚠️ Произошла ошибка при обработке запроса: {str(e)}")

            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()

    def _clean_history(self):
        if len(self.history) > self.MAX_HISTORY_LEN + 1:
            self.history = [self.history[0]] + self.history[-self.MAX_HISTORY_LEN:]


class SessionManager:
    def __init__(self, bot: GuardBot):
        self.bot: GuardBot = bot
        self.sessions: dict[int, ChatSession] = {}

    def session(self, user: discord.User):
        if user.id in self.sessions:
            return self.get_session(user)
        return self.create_session(user)

    def get_session(self, user: discord.User) -> ChatSession | None:
        return self.sessions.get(user.id)

    def create_session(self, user: discord.User) -> ChatSession:
        seance = ChatSession(self.bot)
        self.sessions[user.id] = seance
        return seance

    def delete_session(self, user: discord.User) -> ChatSession:
        return self.sessions.pop(user.id)


async def setup(bot: GuardBot):
    logger.debug(f"⚙️ AiCog loading")
    await bot.add_cog(AiCog(bot))
