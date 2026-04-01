"""Obsługa poleceń weryfikacji"""
import asyncio
import logging
import httpx
import time
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import VERIFY_COST
from database_mysql import Database
from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from youtube.sheerid_verifier import SheerIDVerifier as YouTubeVerifier
from Boltnew.sheerid_verifier import SheerIDVerifier as BoltnewVerifier
from utils.messages import get_insufficient_balance_message, get_verify_usage_message

# Semafory współbieżności (opcjonalnie)
try:
    from utils.concurrency import get_verification_semaphore
except ImportError:
    def get_verification_semaphore(verification_type: str):
        return asyncio.Semaphore(3)

logger = logging.getLogger(__name__)


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /verify — Gemini One Pro"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify", "Gemini One Pro")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    verification_id = OneVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Nieprawidłowy link Verify1D — sprawdź i spróbuj ponownie.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Nie udało się pobrać punktów — spróbuj później.")
        return

    processing_msg = await update.message.reply_text(
        f"Rozpoczynam weryfikację Gemini One Pro...\n"
        f"ID weryfikacji: {verification_id}\n"
        f"Pobrano {VERIFY_COST} pkt\n\n"
        "Proszę czekać, to może zająć 1–2 minuty..."
    )

    try:
        verifier = OneVerifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "gemini_one_pro",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ Weryfikacja zakończona powodzeniem!\n\n"
            if result.get("pending"):
                result_msg += "Dokument przesłany, oczekuje na ręczną weryfikację.\n"
            if result.get("redirect_url"):
                result_msg += f"Link przekierowania:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Weryfikacja nie powiodła się: {result.get('message', 'nieznany błąd')}\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
    except Exception as e:
        logger.error("Błąd weryfikacji: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Błąd podczas przetwarzania: {str(e)}\n\n"
            f"Zwrócono {VERIFY_COST} pkt"
        )


async def verify2_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /verify2 — ChatGPT Teacher K12"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify2", "ChatGPT Teacher K12")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    verification_id = K12Verifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Nieprawidłowy link Verify1D — sprawdź i spróbuj ponownie.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Nie udało się pobrać punktów — spróbuj później.")
        return

    processing_msg = await update.message.reply_text(
        f"Rozpoczynam weryfikację ChatGPT Teacher K12...\n"
        f"ID weryfikacji: {verification_id}\n"
        f"Pobrano {VERIFY_COST} pkt\n\n"
        "Proszę czekać, to może zająć 1–2 minuty..."
    )

    try:
        verifier = K12Verifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "chatgpt_teacher_k12",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ Weryfikacja zakończona powodzeniem!\n\n"
            if result.get("pending"):
                result_msg += "Dokument przesłany, oczekuje na ręczną weryfikację.\n"
            if result.get("redirect_url"):
                result_msg += f"Link przekierowania:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Weryfikacja nie powiodła się: {result.get('message', 'nieznany błąd')}\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
    except Exception as e:
        logger.error("Błąd weryfikacji: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Błąd podczas przetwarzania: {str(e)}\n\n"
            f"Zwrócono {VERIFY_COST} pkt"
        )


async def verify3_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /verify3 — Spotify Student"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify3", "Spotify Student")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # Parsowanie verificationId
    verification_id = SpotifyVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Nieprawidłowy link Verify1D — sprawdź i spróbuj ponownie.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Nie udało się pobrać punktów — spróbuj później.")
        return

    processing_msg = await update.message.reply_text(
        f"🎵 Rozpoczynam weryfikację Spotify Student...\n"
        f"Pobrano {VERIFY_COST} pkt\n\n"
        "📝 Generowanie danych studenta...\n"
        "🎨 Generowanie legitymacji PNG...\n"
        "📤 Wysyłanie dokumentów..."
    )

    semaphore = get_verification_semaphore("spotify_student")

    try:
        async with semaphore:
            verifier = SpotifyVerifier(verification_id)
            result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "spotify_student",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ Weryfikacja Spotify Student zakończona powodzeniem!\n\n"
            if result.get("pending"):
                result_msg += "✨ Dokument przesłany, oczekuje na weryfikację Verify1D\n"
                result_msg += "⏱️ Szacowany czas: kilka minut\n\n"
            if result.get("redirect_url"):
                result_msg += f"🔗 Link przekierowania:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Weryfikacja nie powiodła się: {result.get('message', 'nieznany błąd')}\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
    except Exception as e:
        logger.error("Błąd weryfikacji Spotify: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Błąd podczas przetwarzania: {str(e)}\n\n"
            f"Zwrócono {VERIFY_COST} pkt"
        )


async def verify4_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /verify4 — Bolt.new Teacher (auto kod)"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify4", "Bolt.new Teacher")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # externalUserId lub verificationId
    external_user_id = BoltnewVerifier.parse_external_user_id(url)
    verification_id = BoltnewVerifier.parse_verification_id(url)

    if not external_user_id and not verification_id:
        await update.message.reply_text("Nieprawidłowy link Verify1D — sprawdź i spróbuj ponownie.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Nie udało się pobrać punktów — spróbuj później.")
        return

    processing_msg = await update.message.reply_text(
        f"🚀 Rozpoczynam weryfikację Bolt.new Teacher...\n"
        f"Pobrano {VERIFY_COST} pkt\n\n"
        "📤 Wysyłanie dokumentów..."
    )

    semaphore = get_verification_semaphore("bolt_teacher")

    try:
        async with semaphore:
            verifier = BoltnewVerifier(url, verification_id=verification_id)
            result = await asyncio.to_thread(verifier.verify)

        if not result.get("success"):
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Nie udało się przesłać dokumentu: {result.get('message', 'nieznany błąd')}\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
            return

        vid = result.get("verification_id", "")
        if not vid:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Nie uzyskano ID weryfikacji\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
            return

        await processing_msg.edit_text(
            f"✅ Dokument przesłany!\n"
            f"📋 ID weryfikacji: `{vid}`\n\n"
            f"🔍 Pobieranie kodu weryfikacyjnego...\n"
            f"(maks. 20 s)"
        )

        code = await _auto_get_reward_code(vid, max_wait=20, interval=5)
        
        if code:
            result_msg = (
                f"🎉 Weryfikacja zakończona powodzeniem!\n\n"
                f"✅ Dokument przesłany\n"
                f"✅ Weryfikacja zatwierdzona\n"
                f"✅ Kod pobrany\n\n"
                f"🎁 Kod: `{code}`\n"
            )
            if result.get("redirect_url"):
                result_msg += f"\n🔗 Link przekierowania:\n{result['redirect_url']}"

            await processing_msg.edit_text(result_msg)

            db.add_verification(
                user_id,
                "bolt_teacher",
                url,
                "success",
                f"Code: {code}",
                vid
            )
        else:
            await processing_msg.edit_text(
                f"✅ Dokument przesłany pomyślnie!\n\n"
                f"⏳ Kod jeszcze niedostępny (weryfikacja 1–5 min)\n\n"
                f"📋 ID weryfikacji: `{vid}`\n\n"
                f"💡 Sprawdź później poleceniem:\n"
                f"`/getV4Code {vid}`\n\n"
                f"Punkty zostały pobrane; ponowne sprawdzenie jest bezpłatne."
            )

            db.add_verification(
                user_id,
                "bolt_teacher",
                url,
                "pending",
                "Waiting for review",
                vid
            )
            
    except Exception as e:
        logger.error("Błąd weryfikacji Bolt.new: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Błąd podczas przetwarzania: {str(e)}\n\n"
            f"Zwrócono {VERIFY_COST} pkt"
        )


async def _auto_get_reward_code(
    verification_id: str,
    max_wait: int = 20,
    interval: int = 5
) -> Optional[str]:
    """Pobiera kod nagrody przez lekki polling API."""
    import time
    start_time = time.time()
    attempts = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            elapsed = int(time.time() - start_time)
            attempts += 1
            
            if elapsed >= max_wait:
                logger.info("Timeout pobierania kodu (%s s), użytkownik może użyć /getV4Code", elapsed)
                return None

            try:
                response = await client.get(
                    f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current_step = data.get("currentStep")
                    
                    if current_step == "success":
                        code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
                        if code:
                            logger.info("Pobrano kod automatycznie: %s (po %s s)", code, elapsed)
                            return code
                    elif current_step == "error":
                        logger.warning("Weryfikacja odrzucona: %s", data.get("errorIds", []))
                        return None

                await asyncio.sleep(interval)

            except Exception as e:
                logger.warning("Błąd zapytania o kod: %s", e)
                await asyncio.sleep(interval)
    
    return None


async def verify5_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /verify5 — YouTube Student Premium"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify5", "YouTube Student Premium")
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"])
        )
        return

    # Parsowanie verificationId
    verification_id = YouTubeVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text("Nieprawidłowy link Verify1D — sprawdź i spróbuj ponownie.")
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text("Nie udało się pobrać punktów — spróbuj później.")
        return

    processing_msg = await update.message.reply_text(
        f"📺 Rozpoczynam weryfikację YouTube Student Premium...\n"
        f"Pobrano {VERIFY_COST} pkt\n\n"
        "📝 Generowanie danych studenta...\n"
        "🎨 Generowanie legitymacji PNG...\n"
        "📤 Wysyłanie dokumentów..."
    )

    semaphore = get_verification_semaphore("youtube_student")

    try:
        async with semaphore:
            verifier = YouTubeVerifier(verification_id)
            result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "youtube_student",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = "✅ Weryfikacja YouTube Student Premium zakończona powodzeniem!\n\n"
            if result.get("pending"):
                result_msg += "✨ Dokument przesłany, oczekuje na weryfikację Verify1D\n"
                result_msg += "⏱️ Szacowany czas: kilka minut\n\n"
            if result.get("redirect_url"):
                result_msg += f"🔗 Link przekierowania:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            await processing_msg.edit_text(
                f"❌ Weryfikacja nie powiodła się: {result.get('message', 'nieznany błąd')}\n\n"
                f"Zwrócono {VERIFY_COST} pkt"
            )
    except Exception as e:
        logger.error("Błąd weryfikacji YouTube: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        await processing_msg.edit_text(
            f"❌ Błąd podczas przetwarzania: {str(e)}\n\n"
            f"Zwrócono {VERIFY_COST} pkt"
        )


async def getV4Code_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Polecenie /getV4Code — kod Bolt.new Teacher"""
    user_id = update.effective_user.id

    if db.is_user_blocked(user_id):
        await update.message.reply_text("Jesteś na czarnej liście i nie możesz użyć tej funkcji.")
        return

    if not db.user_exists(user_id):
        await update.message.reply_text("Najpierw zarejestruj się przez /start.")
        return

    if not context.args:
        await update.message.reply_text(
            "Użycie: /getV4Code <verification_id>\n\n"
            "Przykład: /getV4Code 6929436b50d7dc18638890d0\n\n"
            "ID weryfikacji otrzymasz po użyciu /verify4."
        )
        return

    verification_id = context.args[0].strip()

    processing_msg = await update.message.reply_text(
        "🔍 Szukam kodu, proszę czekać..."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
            )

            if response.status_code != 200:
                await processing_msg.edit_text(
                    f"❌ Zapytanie nie powiodło się (HTTP {response.status_code})\n\n"
                    "Spróbuj później lub napisz do administratora."
                )
                return

            data = response.json()
            current_step = data.get("currentStep")
            reward_code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
            redirect_url = data.get("redirectUrl")

            if current_step == "success" and reward_code:
                result_msg = "✅ Sukces!\n\n"
                result_msg += f"🎉 Kod: `{reward_code}`\n\n"
                if redirect_url:
                    result_msg += f"Link przekierowania:\n{redirect_url}"
                await processing_msg.edit_text(result_msg)
            elif current_step == "pending":
                await processing_msg.edit_text(
                    "⏳ Weryfikacja w toku, spróbuj za chwilę.\n\n"
                    "Zwykle trwa 1–5 minut."
                )
            elif current_step == "error":
                error_ids = data.get("errorIds", [])
                await processing_msg.edit_text(
                    f"❌ Weryfikacja nie powiodła się\n\n"
                    f"Szczegóły: {', '.join(error_ids) if error_ids else 'nieznany błąd'}"
                )
            else:
                await processing_msg.edit_text(
                    f"⚠️ Stan: {current_step}\n\n"
                    "Kod jeszcze niedostępny — spróbuj później."
                )

    except Exception as e:
        logger.error("Błąd pobierania kodu Bolt.new: %s", e)
        await processing_msg.edit_text(
            f"❌ Błąd podczas zapytania: {str(e)}\n\n"
            "Spróbuj później lub napisz do administratora."
        )
