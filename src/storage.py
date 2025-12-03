import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Создаем папки если их нет
DATABASE_DIR = "database"
API_CACHE_DIR = ".cache"

for directory in [DATABASE_DIR, API_CACHE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

CACHE_FILE = os.path.join(DATABASE_DIR, "weather_cache.json")
BOT_USERS_FILE = os.path.join(DATABASE_DIR, "bot_users_data.json")


def load_cache() -> Optional[Dict[str, Any]]:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_cache(data: Dict[str, Any]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Не удалось сохранить кэш: {e}")


def is_cache_fresh(cache: Dict[str, Any], max_age_hours: int = 3) -> bool:
    ts = cache.get("fetched_at")
    if not ts:
        return False
    try:
        fetched_at = datetime.fromisoformat(ts)
    except ValueError:
        return False
    now = datetime.now(timezone.utc)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return now - fetched_at <= timedelta(hours=max_age_hours)


def cache_weather(city: Optional[str], latitude: float, longitude: float, weather: Dict[str, Any]) -> None:
    data = {
        "city": city,
        "lat": latitude,
        "lon": longitude,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "weather": weather,
    }
    save_cache(data)


# ============================================================================
# РАБОТА С ДАННЫМИ ПОЛЬЗОВАТЕЛЕЙ БОТА
# ============================================================================

def load_bot_users() -> Dict[str, Any]:
    """Загрузить данные пользователей бота."""
    if not os.path.exists(BOT_USERS_FILE):
        return {}
    try:
        with open(BOT_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_bot_users(data: Dict[str, Any]) -> None:
    """Сохранить данные пользователей бота."""
    try:
        with open(BOT_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Не удалось сохранить данные пользователей бота: {e}")


# ============================================================================
# API КЭШИРОВАНИЕ (10 минут)
# ============================================================================

def get_api_cache_key(lat: float, lon: float, endpoint: str) -> str:
    """Генерировать ключ кэша для API."""
    return f"{lat:.4f}_{lon:.4f}_{endpoint}"


def load_api_cache(lat: float, lon: float, endpoint: str) -> Optional[Dict[str, Any]]:
    """Загрузить данные из API кэша."""
    cache_key = get_api_cache_key(lat, lon, endpoint)
    cache_file = os.path.join(API_CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Проверяем свежесть (10 минут)
        cached_at = datetime.fromisoformat(data.get("cached_at", ""))
        now = datetime.now(timezone.utc)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        
        if now - cached_at <= timedelta(minutes=10):
            return data.get("response")
        
        # Кэш устарел - удаляем
        os.remove(cache_file)
        return None
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_api_cache(lat: float, lon: float, endpoint: str, response: Dict[str, Any]) -> None:
    """Сохранить данные в API кэш."""
    cache_key = get_api_cache_key(lat, lon, endpoint)
    cache_file = os.path.join(API_CACHE_DIR, f"{cache_key}.json")
    
    data = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "response": response
    }
    
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Не удалось сохранить API кэш: {e}")


