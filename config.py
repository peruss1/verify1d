"""Konfiguracja globalna"""
import os
from dotenv import load_dotenv

# Wczytanie pliku .env
load_dotenv()

# Konfiguracja bota Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "verify1dpl")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/verify1dpl")

# Administrator
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))

# Punkty
VERIFY_COST = 1  # Koszt jednej weryfikacji
CHECKIN_REWARD = 1  # Nagroda za codzienne logowanie
INVITE_REWARD = 2  # Nagroda za zaproszenie
REGISTER_REWARD = 1  # Nagroda za rejestrację

# Link pomocy
HELP_NOTION_URL = "https://rhetorical-era-3f3.notion.site/dd78531dbac745af9bbac156b51da9cc"
