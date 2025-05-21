from typing import Iterator


class _EnvObject:
    def __init__(self, env: dict):
        for name, value in env.items():
            setattr(self, name, value)


class _SafeEnvObject:
    def __init__(self, obj: object, /, include_all: bool = True, **filter):
        for name, value in self.__iter__names(obj, include_all, **filter):
            setattr(self, name, value)

    @staticmethod
    def __iter__names(obj: object, include_all: bool, **filter) -> Iterator[tuple[str, object]]:
        for attr in dir(obj):
            condition: bool = False
            try:
                condition = not attr.startswith('_') and attr not in filter and hasattr(obj, attr)
                condition = condition if include_all else not condition
            except DeprecationWarning:
                condition = False
            finally:
                if condition:
                    yield attr, getattr(obj, attr)
