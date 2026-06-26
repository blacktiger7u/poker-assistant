import json
import os
from typing import Any, Dict

# Konfiguracja trzymana w katalogu domowym użytkownika -> działa też dla .exe
APP_DIR = os.path.join(os.path.expanduser("~"), ".poker_assistant")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")

DEFAULTS: Dict[str, Any] = {
    "bankroll": 1000.0,
    "mode": "CASH",            # CASH | MTT
    "position": "BTN",
    "players": "6",
    "sims": "30000",
    "favorite_stakes": [],     # np. ["NL10", "NL25"]
    "sessions": [],            # [{"ts": "...", "result": 12.5, "mode": "CASH"}]
}


def load_settings() -> Dict[str, Any]:
    """Wczytuje ustawienia; brakujące klucze uzupełnia wartościami domyślnymi."""
    merged = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data:
                    merged[key] = data[key]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return merged


def save_settings(data: Dict[str, Any]) -> None:
    """Zapisuje ustawienia. Błędy zapisu są ignorowane (nie blokują aplikacji)."""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        clean = {key: data.get(key, DEFAULTS[key]) for key in DEFAULTS}
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
