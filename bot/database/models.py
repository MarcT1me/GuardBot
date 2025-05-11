from tortoise import Model, fields


class BotDevUsers(Model):
    user_id = fields.BigIntField(pk=True)
    user_name = fields.TextField()


class Server(Model):
    guild_id = fields.BigIntField(pk=True)
    name = fields.TextField()


class Script(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_scripts')

    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=100)

    language = fields.CharField(max_length=50)
    content = fields.TextField()
    is_active = fields.BooleanField(default=False)

    class Meta:
        unique_together = (
            ("server", "type", "name"),
        )


class UserRole(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_roles')

    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=100)

    role_id = fields.BigIntField()
    emoji_id = fields.BigIntField(null=True)


class Template(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_templates')

    name = fields.CharField(max_length=150)

    content = fields.CharField(max_length=5000)

    class Meta:
        unique_together = (
            ("server", "name"),
        )
