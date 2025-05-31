from .bot import GuardBot
from .database import *
from .guard_logger import GuardLogger
from bot.cogs import script_engine
from .cogs import voice_core

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']


def setup_auth():
    import os
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists("secret/token.json"):
        flow = InstalledAppFlow.from_client_secrets_file(
            'secret/gc_client_secret_token.json',
            scopes=SCOPES
        )
        credentials = flow.run_local_server(port=0)
        with open("secret/token.json", "w") as token_file:
            token_file.write(credentials.to_json())


def main():
    import os

    from discord import Intents
    from dotenv import load_dotenv

    from bot.cogs.logging import GuardLogger

    setup_auth()

    intents = Intents.default()
    intents.members = True
    intents.message_content = True

    logger = GuardLogger(logging_active=True)

    db = GuardDatabase()

    guard_bot = GuardBot(
        intents=intents,
        guard_logger=logger,
        database=db
    )

    load_dotenv()
    guard_bot.run(os.getenv("GUARD_BOT_API_KEY"))

    if logger.logging_active:
        logger.stop()

    return GuardBot.is_restart
