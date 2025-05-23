from loguru import logger

if __name__ == "__main__":
    is_restart = True

    while is_restart:
        is_restart = False
        try:
            import bot
            is_restart = bot.main()
        except Exception as e:
            logger.exception("Exception - exit")
        except KeyboardInterrupt:
            logger.exception("KeyboardInterrupt - exit")
