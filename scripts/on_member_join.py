import discord

import bot_core


async def main(bot: bot_core.GuardBot, *, member: discord.Member):
    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"➕ Добро пожаловать, {member.mention}!")

    server_id = member.guild.id
    server_name = member.guild.name

    template: dict = await bot.db.execute("FROM Templates SELECT data IF (ServerID == ?)", server_id)
    role_ids: list = await bot.db.execute("FROM Roles SELECT RoleID IF (ServerID == ?)", server_id)

    role_descriptions = ""

    output = {
        "roles": [],
    }

    for role_id in role_ids:
        role: discord.Role = member.guild.get_role(role_id)
        role_emoji_id = await bot.db.execute(
            "FROM UserRoleEmojis SELECT EmojiID IF (RoleID == ? AND ServerID == ?)",
            role_id, server_id
        )
        output["roles"][role_id] = (role, role_emoji_id)

        role_emoji_description = await bot.db.execute(
            "FROM UserRoleEmojis SELECT Description IF (RoleID == ? AND ServerID == ?)",
            role_id, server_id
        )

        role_emoji: discord.Emoji = member.guild.emojis[role_emoji_id]

        role_descriptions += f"\n{role_emoji} - {role_emoji_description}"

    sent_message = await member.send(
        format(
            template, (
                role_descriptions, server_name
            )
        )
    )

    output["message_id"] = sent_message.id

    return output
