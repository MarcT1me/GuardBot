import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

from .bot import GuardBot
from .database import *
from bot.cogs.script_engine import *
from .cogs import voice_core

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']


def setup_auth():
    if not os.path.exists("secret/token.json"):
        flow = InstalledAppFlow.from_client_secrets_file(
            'secret/gc_client_secret_token.json',
            scopes=SCOPES
        )
        credentials = flow.run_local_server(port=0)
        with open("secret/token.json", "w") as token_file:
            token_file.write(credentials.to_json())


def main():
    setup_auth()

    guard_bot = GuardBot(
        database=GuardDatabase()
    )

    load_dotenv()
    guard_bot.run(os.getenv("GUARD_BOT_API_KEY"))

    return GuardBot.is_restart
