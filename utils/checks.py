"""Narzędzia do sprawdzania i weryfikacji uprawnień"""
import logging
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import CHANNEL_USERNAME

logger = logging.getLogger(__name__)


def is_group_chat(update: Update) -> bool:
    """Określ, czy to czat grupowy"""
    chat = update.effective_chat
    return chat and chat.type in ("group", "supergroup")


async def reject_group_command(update: Update) -> bool:
    """Ograniczenia czatu grupowego: tylko dozwolone /verify /verify2 /verify3 /verify4 /verify5 /qd"""
    if is_group_chat(update):
        await update.message.reply_text("Czaty grupowe obsługują tylko /verify /verify2 /verify3 /verify4 /verify5 /qd，Proszę używać innych poleceń w prywatnej rozmowie。")
        return True
    return False


async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Sprawdź, czy użytkownik dołączył do kanału"""
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError as e:
        logger.error("Nie powiodła się kontrola członków kanału: %s", e)
        return False
