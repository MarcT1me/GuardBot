from .base_script import BaseScript


class LuaScript(BaseScript):
    """Обработчик Lua-скриптов"""
    lang = "lua"

    def compile(self) -> 'LuaScript':
        if self.compiled_code:
            return
        super().compile()

        loader = self.engine.lua_runtime.eval('''
            function(env, code)
                local chunk, err = load(code, nil, 't', env)
                if not chunk then return nil, err end
                return chunk()
            end
        ''')
        success, result = loader(self.code_env, self.code)
        if not success:
            raise RuntimeError(f"Lua error: {result}")

        if self.is_lib:
            self._update_main_func()

        return self
