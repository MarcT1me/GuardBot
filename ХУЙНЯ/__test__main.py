import os
import sqlite3
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Set

import discord
from discord import app_commands
from discord.ext import commands


class DatabaseManager:
    """Класс для управления базой данных с соблюдением SRP"""

    def __init__(self, db_name: str = 'guard_data.db'):
        self.conn = sqlite3.connect(db_name)
        self._init_db()
        self.conn.row_factory = sqlite3.Row  # Для доступа к полям по имени

    def _init_db(self):
        """Инициализация структуры базы данных"""
        with self.conn:
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS roles (
                    role_id INTEGER PRIMARY KEY,
                    role_name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMP NOT NULL,
                    roles TEXT NOT NULL
                );
            ''')

    async def save_roles(self, roles: List[discord.Role]):
        """Сохраняет или обновляет роли в базе данных"""
        with self.conn:
            for role in roles:
                self.conn.execute('''
                    INSERT OR REPLACE INTO roles 
                    VALUES (?, ?, ?, ?)
                ''', (role.id, role.name, str(role.color), role.created_at.isoformat()))

    async def save_users(self, members: List[discord.Member]):
        """Сохраняет или обновляет пользователей в базе данных"""
        with self.conn:
            for member in members:
                roles = ','.join(str(r.id) for r in member.roles)
                self.conn.execute('''
                    INSERT OR REPLACE INTO users 
                    VALUES (?, ?, ?, ?)
                ''', (member.id, member.display_name,
                      member.joined_at.isoformat(), roles))

    async def get_unused_roles(self, guild: discord.Guild) -> Set[str]:
        """Возвращает неиспользуемые роли с обработкой ошибок"""
        try:
            # Получаем использованные роли
            used_roles = await self._get_used_roles(guild)

            # Получаем все ID ролей сервера
            all_roles = {role.id for role in guild.roles}

            # Исключаем дефолтную роль и managed-роли
            unused_ids = all_roles - used_roles - {guild.default_role.id}
            unused_ids = {rid for rid in unused_ids
                          if not guild.get_role(rid).managed}

            if not unused_ids:
                return set()

            return await self._fetch_unused_roles(unused_ids)

        except Exception as e:
            print(f"Error getting unused roles: {str(e)}")
            return set()

    async def _get_used_roles(self, guild: discord.Guild) -> Set[int]:
        """Получает набор используемых ролей"""
        used_roles = set()
        for member in guild.members:
            used_roles.update(r.id for r in member.roles)
        return used_roles

    async def _fetch_unused_roles(self, role_ids: Set[int]) -> Set[str]:
        """Выполняет запрос к базе данных"""
        try:
            query = f'''
                SELECT role_name 
                FROM roles 
                WHERE role_id IN ({','.join('?' for _ in role_ids)})
            '''
            cursor = self.conn.execute(query, tuple(role_ids))
            return {row['role_name'] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            print(f"Database query failed: {str(e)}")
            return set()


class UserCommands(commands.Cog):
    """Ког для команд связанных с пользователями"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @app_commands.command(name="joined", description="Показывает стаж пользователя")
    async def get_join_date(self, interaction: discord.Interaction,
                            member: Optional[discord.Member] = None):
        target = member or interaction.user

        if not target.joined_at:
            return await interaction.response.send_message("Данные о присоединении недоступны", ephemeral=True)

        try:
            # Приводим оба времени к aware-формату
            now = datetime.now(timezone.utc)
            joined_at = target.joined_at.replace(tzinfo=timezone.utc)

            delta = relativedelta(now, joined_at)
            embed = self._create_user_embed(target, delta)

        except Exception as e:
            self.logger.error(f"Error in joined command: {str(e)}")
            embed = discord.Embed(
                title="⚠️ Ошибка",
                description="Не удалось получить информацию",
                color=0xFF0000
            )

        await interaction.response.send_message(embed=embed)

    def _create_user_embed(self, member: discord.Member,
                           delta: relativedelta) -> discord.Embed:
        """Фабрика для создания Embed (принцип SRP)"""
        highest_role = max(member.roles, key=lambda r: r.position)

        return discord.Embed(
            title=f"📊 Статистика {member.display_name}",
            description=(
                f"**Дата присоединения:**\n{member.joined_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"**Стаж:** {delta.years} лет, {delta.months} мес., {delta.days} дн.\n"
                f"**Высшая роль:** {highest_role.mention}"
            ),
            color=highest_role.color
        ).set_thumbnail(url=member.avatar.url)


class RoleCommands(commands.Cog):
    """Ког для управления ролями"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @app_commands.command(name="list_roles", description="Анализ ролей сервера")
    async def list_roles(self, interaction: discord.Interaction):
        """Показать статистику по ролям"""
        guild = interaction.guild
        unused_roles = await self.db.get_unused_roles(guild)

        embed = discord.Embed(
            title="📚 Роли сервера",
            description=f"Всего ролей: {len(guild.roles)}",
            color=0x2F3136
        ).add_field(
            name="Неиспользуемые роли",
            value='\n'.join(f'• {r}' for r in unused_roles) or "Отсутствуют",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


class BotClient(commands.Bot):
    """Основной класс бота с Dependency Injection"""

    def __init__(self, db: DatabaseManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def setup_hook(self):
        """Инициализация когов при запуске"""
        await self.add_cog(UserCommands(self, self.db))
        await self.add_cog(RoleCommands(self, self.db))

    async def on_ready(self):
        """Обработчик события готовности"""
        await self._sync_commands()
        await self._scan_server_data()
        print(f"✅ Бот {self.user} готов к работе!")

    async def _sync_commands(self):
        """Синхронизация команд с Discord API"""
        await self.tree.sync()
        print("🔁 Команды синхронизированы")

    async def _scan_server_data(self):
        """Сканирование данных сервера"""
        for guild in self.guilds:
            await self.db.save_roles(guild.roles)
            await self.db.save_users(guild.members)
        print("🔍 Данные сервера сохранены в БД")


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    db_manager = DatabaseManager()
    bot = BotClient(
        db=db_manager,
        command_prefix='/',
        intents=intents,
        help_command=None
    )

    bot.run(os.getenv("GUARD_BOT_API_KEY"))
