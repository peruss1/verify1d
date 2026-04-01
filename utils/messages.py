"""Szablony wiadomości"""
from config import CHANNEL_URL, VERIFY_COST, HELP_NOTION_URL


def get_welcome_message(full_name: str, invited_by: bool = False) -> str:
    """Pobiera wiadomość powitalną"""
    msg = (
        f"🎉 Witaj, {full_name}!\n"
        "Zostałeś pomyślnie zarejestrowany i otrzymałeś 1 punkt.\n"
    )
    if invited_by:
        msg += "Dziękujemy za dołączenie przez link zaproszenia — osoba zapraszająca otrzymała 2 punkty.\n"

    msg += (
        "\nTen bot automatycznie wykonuje weryfikację Verify1D.\n"
        "Szybki start:\n"
        "/about - informacje o funkcjach bota\n"
        "/balance - sprawdź saldo punktów\n"
        "/help - pełna lista komend\n\n"
        "Jak zdobyć więcej punktów:\n"
        "/qd - codzienne logowanie\n"
        "/invite - zaproś znajomych\n"
        f"Dołącz do kanału: {CHANNEL_URL}"
    )
    return msg


def get_about_message() -> str:
    """Pobiera wiadomość 'o bocie'"""
    return (
        "🤖 Bot do automatycznej weryfikacji Verify1D\n"
        "\n"
        "Funkcje:\n"
        "- Automatyczna weryfikacja Verify1D dla uczniów/nauczycieli\n"
        "- Obsługuje Gemini One Pro, ChatGPT Teacher K12, Spotify Student, YouTube Student, Bolt.new Teacher\n"
        "\n"
        "Zdobywanie punktów:\n"
        "- Rejestracja: +1 punkt\n"
        "- Codzienne logowanie: +1 punkt\n"
        "- Zaproszenie znajomego: +2 punkty/os.\n"
        "- Użycie kodu (wg zasad kodu)\n"
        f"- Dołącz do kanału: {CHANNEL_URL}\n"
        "\n"
        "Jak używać:\n"
        "1. Rozpocznij weryfikację na stronie i skopiuj pełny link\n"
        "2. Wyślij /verify, /verify2, /verify3, /verify4 lub /verify5 z tym linkiem\n"
        "3. Poczekaj na przetworzenie i sprawdź wynik\n"
        "4. Bolt.new automatycznie pobiera kod — ręcznie: /getV4Code <verification_id>\n"
        "\n"
        "Autor: peruss1\n"
        "Więcej komend: /help"
    )


def get_help_message(is_admin: bool = False) -> str:
    """Pobiera wiadomość pomocy"""
    msg = (
        "📖 Bot Verify1D — pomoc\n"
        "\n"
        "Komendy użytkownika:\n"
        "/start - rozpocznij (rejestracja)\n"
        "/about - informacje o bocie\n"
        "/balance - sprawdź saldo punktów\n"
        "/qd - codzienne logowanie (+1 punkt)\n"
        "/invite - link zaproszenia (+2 punkty/os.)\n"
        "/use <kod> - użyj kodu doładowania\n"
        f"/verify <link> - Gemini One Pro (koszt: -{VERIFY_COST} punktów)\n"
        f"/verify2 <link> - ChatGPT Teacher K12 (koszt: -{VERIFY_COST} punktów)\n"
        f"/verify3 <link> - Spotify Student (koszt: -{VERIFY_COST} punktów)\n"
        f"/verify4 <link> - Bolt.new Teacher (koszt: -{VERIFY_COST} punktów)\n"
        f"/verify5 <link> - YouTube Student Premium (koszt: -{VERIFY_COST} punktów)\n"
        "/getV4Code <verification_id> - pobierz kod Bolt.new\n"
        "/help - pokaż tę wiadomość\n"
        f"Pomoc przy błędach: {HELP_NOTION_URL}\n"
    )

    if is_admin:
        msg += (
            "\nKomendy administratora:\n"
            "/addbalance <ID użytkownika> <punkty> - dodaj punkty\n"
            "/block <ID użytkownika> - zablokuj użytkownika\n"
            "/white <ID użytkownika> - odblokuj użytkownika\n"
            "/blacklist - lista zablokowanych\n"
            "/genkey <kod> <punkty> [ilość] [dni] - generuj kody\n"
            "/listkeys - lista kodów\n"
            "/broadcast <tekst> - wyślij wiadomość do wszystkich\n"
        )

    return msg


def get_insufficient_balance_message(current_balance: int) -> str:
    """Pobiera komunikat o braku punktów"""
    return (
        f"Za mało punktów! Wymagane: {VERIFY_COST}, masz: {current_balance}.\n\n"
        "Jak zdobyć punkty:\n"
        "- codzienne logowanie /qd\n"
        "- zapraszanie znajomych /invite\n"
        "- użycie kodu /use <kod>"
    )


def get_verify_usage_message(command: str, service_name: str) -> str:
    """Pobiera instrukcję użycia komendy weryfikacji"""
    return (
        f"Sposób użycia: {command} <link Verify1D>\n\n"
        "Przykład:\n"
        f"{command} https://services.sheerid.com/verify/xxx/?verificationId=xxx\n\n"
        "Jak zdobyć link:\n"
        f"1. Wejdź na stronę weryfikacji {service_name}\n"
        "2. Rozpocznij proces\n"
        "3. Skopiuj pełny URL z przeglądarki\n"
        f"4. Użyj komendy {command}"
    )
    
