from tortoise import Model, fields


class Server(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField(unique=True)
    scripts = fields.JSONField(default={})
    roles = fields.JSONField(default={})


class Script(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    content = fields.TextField()
    server = fields.ForeignKeyField('models.Server', related_name='scripts')
    is_active = fields.BooleanField(default=True)


class UserRole(Model):
    id = fields.IntField(pk=True)
    role_id = fields.BigIntField()
    server = fields.ForeignKeyField('models.Server', related_name='roles')
    emoji_id = fields.BigIntField(null=True)
    description = fields.TextField(null=True)
