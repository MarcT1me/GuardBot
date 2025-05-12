from tortoise import Model, fields


class BotDevUsers(Model):
    user_id = fields.BigIntField(pk=True)
    user_name = fields.TextField()


class Server(Model):
    guild_id = fields.BigIntField(pk=True)
    name = fields.TextField()

    is_active = fields.BooleanField(default=False)

    additions = fields.JSONField(default={})  # any data


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


class User(Model):
    id = fields.BigIntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_users')

    roles = fields.JSONField(default={})  # role_id
    scripts = fields.JSONField(default={})  # script_id
    additions = fields.JSONField(default={})  # any data


class Role(Model):
    id = fields.BigIntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_roles')

    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=100)

    emoji_id = fields.BigIntField(null=True)
    is_active = fields.BooleanField(default=False)


class Channel(Model):
    id = fields.BigIntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_channels')

    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=100)
    is_active = fields.BooleanField(default=False)
    additions = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("server", "type", "name"),
        )


class Template(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_templates')

    name = fields.CharField(max_length=150)

    content = fields.CharField(max_length=5000)
    is_active = fields.BooleanField(default=False)

    class Meta:
        unique_together = (
            ("server", "name"),
        )
