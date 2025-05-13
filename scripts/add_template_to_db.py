async def main(*, bot, interaction):
    guild = interaction.guild

    #     await bot.db.save_template(
    #         guild.id,
    #         "greetings_list",
    #         ""
    #         "➕ Бобро поржаловать, {member.mention}!\\"
    #         "➕ Встречайте: {member.mention}\\"
    #         "➕ Дарова, {member.mention}\\"
    #         "➕ У нас новый бибус: {member.mention}\\"
    #         "➕ Коничива: {member.mention}"
    #     )
    #
    #     await bot.db.save_template(
    #         guild.id,
    #         "join_message_title",
    #         "**Добро пожаловать на {member.guild.name}!**"
    #     )
    #     await bot.db.save_template(
    #         guild.id,
    #         "join_message_description",
    #         """{member.mention}, рады видеть тебя на нашем сервере {member.guild.name}!
    # Это сервер для всех, кто любит компы, люди, которые хотят пообщаться, геймеры и даже программисты.
    #
    #     Я, {member.guild.me.mention}, помогаю администраторам и не только на сервере.
    # Пройдись по путеводителю и прочитай все правила, не забудь зарегистрироваться в соответствующем канале.
    #
    #     Можешь почитать или поспрашивать других пользователей о том, что я умею. К сожалению Я сейчас в разработке
    # и парой могу нести чушь или сделать что-то, не так."""
    #     )
    #     await bot.db.save_template(
    #         guild.id,
    #         "join_message_footer",
    #         "Photo by @protokops. Member #{member.guild.member_count}"
    #     )
    #
    #     await bot.db.save_template(
    #         guild.id,
    #         "voice_channel_create",
    #         """
    #         🎤 Новая комната\\ {member.mention} создал комнату {temp_channel.mention}\n
    # настройки:\n
    # > имя: `{option.name}`\n
    # > изменения: `{option.change_allows}`\n
    # > размер: `{option.size}`
    # \\создатель {author.name}, фабрика: {parent_channel.name}"""
    #     )
    #
    #     await bot.db.save_template(
    #         guild.id,
    #         "voice_channel_delete",
    #         """🚪 Комната удалена\\{member.mention} покинул комнату `{temp_channel.name}`"
    # "\\создатель {author.name}, фабрика: {parent_channel.name}"""
    #     )
    templates = [
        {
            "name": "greetings_list",
            "content": "➕ Бобро поржаловать, {member.mention}!\\"
                       "➕ Встречайте: {member.mention}\\"
                       "➕ Дарова, {member.mention}\\"
                       "➕ У нас новый бибус: {member.mention}\\"
                       "➕ Коничива: {member.mention}"
        },
        {
            "name": "join_message_title",
            "content": "**Добро пожаловать на {member.guild.name}!**"
        },
        {
            "name": "join_message_description",
            "content":
                """    {member.mention}, рады видеть тебя на нашем сервере {member.guild.name}!
Это сервер для всех, кто любит компы, люди, которые хотят пообщаться, геймеры и даже программисты.

    Я, {member.guild.me.mention}, помогаю администраторам и не только на сервере.
Пройдись по путеводителю и прочитай все правила, не забудь зарегистрироваться в соответствующем канале.

    Можешь почитать или поспрашивать других пользователей о том, что я умею. К сожалению Я сейчас в разработке
и парой могу нести чушь или сделать что-то, не так."""
        },
        {
            "name": "join_message_footer",
            "content": "Photo by @protokops. Member #{member.guild.member_count}"
        },
        {
            "name": "voice_channel_create",
            "content":
                """🎤 Новая комната\\
{member.mention} создал комнату {temp_channel.mention}
настройки:
> имя: `{option.name}`
> изменения: `{option.change_allows}`
> размер: `{option.size}`\\
создатель {author.name}, фабрика: {parent_channel.name}"""
        },
        {
            "name": "voice_channel_delete",
            "content":
                """🚪 Комната удалена\\
{member.mention} покинул комнату `{temp_channel.name}`\\
создатель {author.name}, фабрика: {parent_channel.name}"""
        }
    ]

    for template_data in templates:
        await bot.db.save_template(
            guild.id,
            template_data["name"],
            template_data["content"]
        )

    await interaction.channel.send("Templates added to DataBase")
