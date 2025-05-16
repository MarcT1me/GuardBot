from tortoise import Model, fields


class Server(Model):
    guild_id = fields.BigIntField(pk=True)

    is_active = fields.BooleanField(default=False)

    additions = fields.JSONField(default={})  # any data


class User(Model):
    id = fields.BigIntField(pk=True)
    user_id = fields.BigIntField()
    server = fields.ForeignKeyField('models.Server', related_name='server_users')

    roles = fields.JSONField(default={})

    additions = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("server", "user_id"),
        )


class Script(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_scripts')

    type = fields.CharField(max_length=50)
    name = fields.CharField(max_length=100)

    content = fields.TextField()
    is_active = fields.BooleanField(default=False)

    additions = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("server", "type", "name"),
        )


class Role(Model):
    id = fields.BigIntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_roles')

    emoji_id = fields.BigIntField(null=True)
    is_active = fields.BooleanField(default=False)

    additions = fields.JSONField(default={})  # any data


class Channel(Model):
    id = fields.BigIntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_channels')

    type = fields.CharField(max_length=50)

    additions = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("id", "server", "type"),
        )


class Template(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField('models.Server', related_name='server_templates')

    name = fields.CharField(max_length=150)

    content = fields.CharField(max_length=4000)
    is_active = fields.BooleanField(default=False)

    class Meta:
        unique_together = (
            ("server", "name"),
        )
