from bot.script_env import *

templates = [
    {
        "name": "greetings_list",
        "content": "➕ Бобро поржаловать, {member.mention}!\\"
                   "➕ Greetings: {member.mention}!\\"
                   "➕ Hi, {member.mention}!\\"
                   "➕ Hay! We have a new member: {member.mention}!\\"
                   "➕ Konichiwa: {member.mention}!"
    },
    {
        "name": "join_message_title",
        "content": "**Welcome to {member.guild.name}!**"
    },
    {
        "name": "join_message_description",
        "content":
            """
RU:
    {member.mention}, рады видеть тебя на нашем сервере {member.guild.name}!
Это сервер для всех, кто любит компы, люди, которые хотят пообщаться, геймеры и даже программисты.

Я, {member.guild.me.mention}, помогаю администраторам и не только на сервере.
Пройдись по путеводителю и прочитай все правила, не забудь зарегистрироваться в соответствующем канале.

Можешь почитать или поспрашивать других пользователей о том, что я умею. К сожалению Я сейчас в разработке
и парой могу нести чушь или сделать что-то, не так.
ENG:
    {member.mention}, we are glad to see you on our server {member.guild.name}!
This is a server for everyone who loves computers, who want to chatting, gamers and even programmers.

I, {member.guild.me.mention}, I help administrators, and not only on the our server.
Check out the manual, don't forget to read all the rules.

You can read or ask other users about what I can do. Unfortunately, I'm currently in development
and I can talk nonsense or do something wrong."""
    },
    {
        "name": "join_message_footer",
        "content": "Photo by @protokops. Member #{member.guild.member_count}"
    },
    {
        "name": "voice_channel_create",
        "content":
            """🎤 New room\\
{member.mention} created a new channel {temp_channel.mention}
parameters:
> room name: `{option.name.name}`
> access to changes: `{option.change_allows.name}`
> room size: `{option.size}`\\
creator {author.name}, factory: {parent_channel.name}"""
    },
    {
        "name": "voice_channel_delete",
        "content":
            """🚪 Room deleted\\
{member.mention} has left the channel `{temp_channel.name}`\\
creator {author.name}, factory: {parent_channel.name}"""
    },
    {
        "name": "voice_channel_join",
        "content":
            """➕ Join into room\\
{member.mention} join into {temp_channel.mention}\\
creator {author.name}, factory: {parent_channel.name}"""
    },
    {
        "name": "voice_channel_disconnect",
        "content":
            """➖ Disconnect from room\\
{member.mention} has left from {temp_channel.mention}\\
creator {author.name}, factory: {parent_channel.name}"""
    },
    {
        "name": "farewell_list",
        "content": "User {member.mention} has left us\\"
                   "Thank you for visiting, {member.mention}!\\"
                   "Goodbye, {member.mention}\\"
                   "See you later, {member.mention}"
    },
]


async def init(bot: Bot):
    for template_data in templates:
        await bot.guild.db.save_template(
            name=template_data["name"],
            content=template_data["content"]
        )
