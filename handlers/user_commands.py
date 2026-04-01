"""Obsługa poleceń użytkownika"""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command
from utils.messages import (
    get_welcome_message,
    get_about_message,
    get_help_message,
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /start"""
    if await reject_group_command(update):
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    full_name = user.full_name or ""

    if db.user_exists(user_id):
        await update.message.reply_text(
            f"Witaj ponownie, {full_name}!\n"
            "Konto jest już zarejestrowane.\n"
            "Wyślij /help, aby zobaczyć polecenia."
        )
        return

    invited_by: Optional[int] = None
    if context.args:
        try:
            invited_by = int(context.args[0])
            if not db.user_exists(invited_by):
                invited_by = None
        except Exception:
            invited_by = None

    if db.create_user(user_id, username, full_name, invited_by):
        welcome_msg = get_welcome_message(full_name, bool(invited_by))
        await update.message.reply_text(welcome_msg)
    else:
        await update.message.reply_text("Rejestracja nie powiodła się — spróbuj później.")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /about"""
    if await reject_group_command(update):
        return

    await update.message.reply_text(get_about_message())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /help"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_USER_ID
    await update.message.reply_text(get_help_message(is_admin))


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /balance"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    await update.message.reply_text(
        f"💰 Saldo punktów\n\nAktualnie: {user['balance']} pkt"
    )


async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /qd — codzienne logowanie"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not db.can_checkin(user_id):
        await update.message.reply_text("❌ Dzisiaj już się zalogowałeś — wróć jutro.")
        return

    if db.checkin(user_id):
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"✅ Logowanie udane!\n+1 pkt\nSaldo: {user['balance']} pkt"
        )
    else:
        await update.message.reply_text("❌ Dzisiaj już się zalogowałeś — wróć jutro.")


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /invite"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
        f"🎁 Twój link zaproszenia:\n{invite_link}\n\n"
        "Za każdego zaproszonego, który się zarejestruje, otrzymasz 2 pkt."
    )


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /use — kod doładowania"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            "Użycie: /use <kod>\n\nPrzykład: /use wandouyu"
        )
        return

    key_code = context.args[0].strip()
    result = db.use_card_key(key_code, user_id)

    if result is None:
        await update.message.reply_text("Nie ma takiego kodu — sprawdź wpis.")
    elif result == -1:
        await update.message.reply_text("Ten kod osiągnął limit użyć.")
    elif result == -2:
        await update.message.reply_text("Ten kod wygasł.")
    elif result == -3:
        await update.message.reply_text("Ten kod został już przez Ciebie wykorzystany.")
    else:
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"Kod zastosowany!\n+{result} pkt\nSaldo: {user['balance']} pkt"
        )
