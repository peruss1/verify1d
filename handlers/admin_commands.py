"""Obsługa poleceń administratora"""
import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command

logger = logging.getLogger(__name__)


async def addbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/addbalance — dodaj punkty"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Użycie: /addbalance <ID użytkownika> <punkty>\n\nPrzykład: /addbalance 123456789 10"
        )
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])

        if not db.user_exists(target_user_id):
            await update.message.reply_text("Użytkownik nie istnieje.")
            return

        if db.add_balance(target_user_id, amount):
            user = db.get_user(target_user_id)
            await update.message.reply_text(
                f"✅ Dodano {amount} pkt użytkownikowi {target_user_id}.\n"
                f"Aktualne saldo: {user['balance']}"
            )
        else:
            await update.message.reply_text("Operacja nie powiodła się — spróbuj później.")
    except ValueError:
        await update.message.reply_text("Zły format — podaj prawidłowe liczby.")


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/block — zablokuj użytkownika"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    if not context.args:
        await update.message.reply_text(
            "Użycie: /block <ID użytkownika>\n\nPrzykład: /block 123456789"
        )
        return

    try:
        target_user_id = int(context.args[0])

        if not db.user_exists(target_user_id):
            await update.message.reply_text("Użytkownik nie istnieje.")
            return

        if db.block_user(target_user_id):
            await update.message.reply_text(f"✅ Użytkownik {target_user_id} zablokowany.")
        else:
            await update.message.reply_text("Operacja nie powiodła się — spróbuj później.")
    except ValueError:
        await update.message.reply_text("Zły format ID użytkownika.")


async def white_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/white — odblokuj użytkownika"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    if not context.args:
        await update.message.reply_text(
            "Użycie: /white <ID użytkownika>\n\nPrzykład: /white 123456789"
        )
        return

    try:
        target_user_id = int(context.args[0])

        if not db.user_exists(target_user_id):
            await update.message.reply_text("Użytkownik nie istnieje.")
            return

        if db.unblock_user(target_user_id):
            await update.message.reply_text(f"✅ Użytkownik {target_user_id} odblokowany.")
        else:
            await update.message.reply_text("Operacja nie powiodła się — spróbuj później.")
    except ValueError:
        await update.message.reply_text("Zły format ID użytkownika.")


async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/blacklist — lista zablokowanych"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    blacklist = db.get_blacklist()

    if not blacklist:
        await update.message.reply_text("Czarna lista jest pusta.")
        return

    msg = "📋 Czarna lista:\n\n"
    for user in blacklist:
        msg += f"ID: {user['user_id']}\n"
        msg += f"Nick: @{user['username']}\n"
        msg += f"Imię: {user['full_name']}\n"
        msg += "---\n"

    await update.message.reply_text(msg)


async def genkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/genkey — generuj kody"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Użycie: /genkey <kod> <punkty> [max użyć] [dni ważności]\n\n"
            "Przykłady:\n"
            "/genkey wandouyu 20 — 20 pkt, jednorazowo, bez wygaśnięcia\n"
            "/genkey vip100 50 10 — 50 pkt, max 10 użyć, bez wygaśnięcia\n"
            "/genkey temp 30 1 7 — 30 pkt, jednorazowo, wygasa po 7 dniach"
        )
        return

    try:
        key_code = context.args[0].strip()
        balance = int(context.args[1])
        max_uses = int(context.args[2]) if len(context.args) > 2 else 1
        expire_days = int(context.args[3]) if len(context.args) > 3 else None

        if balance <= 0:
            await update.message.reply_text("Liczba punktów musi być większa od 0.")
            return

        if max_uses <= 0:
            await update.message.reply_text("Limit użyć musi być większy od 0.")
            return

        if db.create_card_key(key_code, balance, user_id, max_uses, expire_days):
            msg = (
                "✅ Kod utworzony!\n\n"
                f"Kod: {key_code}\n"
                f"Punkty: {balance}\n"
                f"Użycia: {max_uses}\n"
            )
            if expire_days:
                msg += f"Ważność: {expire_days} dni\n"
            else:
                msg += "Ważność: bez limitu\n"
            msg += f"\nDla użytkownika: /use {key_code}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Kod już istnieje lub nie udało się go utworzyć — użyj innej nazwy.")
    except ValueError:
        await update.message.reply_text("Zły format — podaj prawidłowe liczby.")


async def listkeys_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/listkeys — lista kodów"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    keys = db.get_all_card_keys()

    if not keys:
        await update.message.reply_text("Brak kodów.")
        return

    msg = "📋 Kody:\n\n"
    for key in keys[:20]:
        msg += f"Kod: {key['key_code']}\n"
        msg += f"Punkty: {key['balance']}\n"
        msg += f"Użycia: {key['current_uses']}/{key['max_uses']}\n"

        if key["expire_at"]:
            expire_time = datetime.fromisoformat(key["expire_at"])
            if datetime.now() > expire_time:
                msg += "Stan: wygasł\n"
            else:
                days_left = (expire_time - datetime.now()).days
                msg += f"Stan: aktywny (zostało ~{days_left} dni)\n"
        else:
            msg += "Stan: bez wygaśnięcia\n"

        msg += "---\n"

    if len(keys) > 20:
        msg += f"\n(pokazano 20 z {len(keys)})"

    await update.message.reply_text(msg)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """/broadcast — wiadomość do wszystkich"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Brak uprawnień do tego polecenia.")
        return

    text = " ".join(context.args).strip() if context.args else ""
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""

    if not text:
        await update.message.reply_text("Użycie: /broadcast <tekst> albo odpowiedz na wiadomość i wyślij /broadcast")
        return

    user_ids = db.get_all_user_ids()
    success, failed = 0, 0

    status_msg = await update.message.reply_text(f"📢 Wysyłka do {len(user_ids)} użytkowników...")

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("Broadcast do %s nie powiódł się: %s", uid, e)
            failed += 1

    await status_msg.edit_text(f"✅ Zakończono.\nWysłano: {success}\nBłędy: {failed}")
