import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

CACHE_FILE = "weather_cache.json"


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


