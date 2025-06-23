import ast

from .base_script import BaseScript


class PythonScript(BaseScript):
    """Обработчик Python-скриптов"""
    lang = "py"

    def compile(self) -> 'PythonScript':
        if self.compiled_code:
            return self
        self.normalize()
        self._validate_syntax()

        super().compile()

        exec(
            self.compiled_code,
            self.code_env
        )

        if not self.is_lib:
            self._update_main_func()

        return self

    def normalize(self) -> None:
        context = self.code.replace("from bot.script_env import *", "")
        context = context.replace("GuardBot", "Any")

        new_content = ""
        for line in context.split("\n"):
            if "import" in line:
                if "__import__" in line:
                    raise ImportError(f"Not allow builtins: __import__")

                data = line.split()
                name = data[1].replace("lib.", "")

                if not self.engine.get_script(self.env_guild_id, name):
                    raise ImportError(f"Script {name} not found")

                l = len(data)
                if l == 2:
                    line = f"include(\"{name}\")"
                elif l == 4:
                    as_name = data[3]
                    line = f"include(\"{name}\", \"{as_name}\")"

            new_content += line + "\n"

        self.compiled_code = new_content

    def _validate_syntax(self) -> None:
        """AST-валидация с разрешением асинхронных конструкций"""
        forbidden_nodes = (
            ast.ImportFrom,
            ast.Import,
            ast.Lambda,
            ast.With,
            # Добавляем исключения для async/await
        )

        for node in ast.walk(ast.parse(self.compiled_code)):
            if isinstance(node, forbidden_nodes):
                if isinstance(node, ast.Call):
                    func_name = getattr(node.func, 'id', '')
                    if func_name in ('eval', 'exec', 'open'):
                        raise SyntaxError(f"Dangerous function: {func_name}")
                else:
                    raise SyntaxError(f"Forbidden: {type(node).__name__}")

            # Разрешаем async def и await
            if isinstance(node, ast.AsyncFunctionDef):
                pass  # Явно разрешаем
            if isinstance(node, ast.Await):
                pass  # Явно разрешаем
