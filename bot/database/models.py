from tortoise import Model, fields


class Server(Model):
    guild_id: int = fields.BigIntField(pk=True)

    is_active: bool = fields.BooleanField(default=False)

    additions: dict = fields.JSONField(default={})  # any data


class User(Model):
    id: int = fields.BigIntField(pk=True)
    user_id: int = fields.BigIntField()
    server: Server = fields.ForeignKeyField('models.Server', related_name='server_users')

    roles: list = fields.JSONField(default=[])
    additions: dict = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("server", "user_id"),
        )


class Script(Model):
    id: int = fields.IntField(pk=True)
    server: Server = fields.ForeignKeyField('models.Server', related_name='server_scripts')

    type: str = fields.CharField(max_length=50)
    name: str = fields.CharField(max_length=100)

    content: str = fields.TextField()
    is_active: bool = fields.BooleanField(default=False)

    additions: dict = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("server", "type", "name"),
        )


class Role(Model):
    id: int = fields.BigIntField(pk=True)
    server: Server = fields.ForeignKeyField('models.Server', related_name='server_roles')

    emoji_id: int = fields.BigIntField(null=True)
    is_active: bool = fields.BooleanField(default=False)

    additions: dict = fields.JSONField(default={})  # any data


class Channel(Model):
    id: int = fields.BigIntField(pk=True)
    server: Server = fields.ForeignKeyField('models.Server', related_name='server_channels')

    type: str = fields.CharField(max_length=50)

    additions: dict = fields.JSONField(default={})  # any data

    class Meta:
        unique_together = (
            ("id", "server", "type"),
        )


class Template(Model):
    id: int = fields.IntField(pk=True)
    server: Server = fields.ForeignKeyField('models.Server', related_name='server_templates')

    name: str = fields.CharField(max_length=150)

    content: str = fields.CharField(max_length=4000)
    is_active: bool = fields.BooleanField(default=False)

    class Meta:
        unique_together = (
            ("server", "name"),
        )
