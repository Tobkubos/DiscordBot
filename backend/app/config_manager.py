import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
CONFIG_FILE = "guild_configs.json"

def _load_all_configs() -> Dict[str, Dict[str, Any]]:
    """Odczytuje konfiguracje wszystkich serwerów z pliku."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Błąd podczas odczytu pliku konfiguracji: {e}")
    return {}

def _save_all_configs(configs: Dict[str, Dict[str, Any]]):
    """Zapisuje konfiguracje na dysk."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Błąd podczas zapisu pliku konfiguracji: {e}")

def save_guild_config(guild_id: str, config_data: Dict[str, Any]):
    """Zapisuje kompletną konfigurację dla danego serwera Discord."""
    configs = _load_all_configs()
    configs[guild_id] = config_data
    _save_all_configs(configs)

def get_active_text_model(guild_id: str) -> Optional[str]:
    """
    Zwraca wybrany model dla serwera. 
    Zwraca None, jeśli konfiguracja nie istnieje lub model jest ustawiony na 'none'.
    """
    configs = _load_all_configs()
    guild_config = configs.get(guild_id, {})
    model = guild_config.get("active_text_model", "none")
    
    if not model or model.lower() == "none":
        return None
    return model