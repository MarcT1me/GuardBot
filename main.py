from loguru import logger
import importlib

if __name__ == "__main__":
    is_error = False
    is_restart = True

    while is_error or is_restart:
        try:
            bot = importlib.import_module("bot", "bot")
            is_restart = bot.main()
        except Exception as e:
            logger.exception("Exception - restart")
            is_error = True
        except KeyboardInterrupt:
            logger.exception("KeyboardInterrupt - exit")
