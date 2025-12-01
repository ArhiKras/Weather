import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timezone, timedelta
import time
from typing import Optional, Tuple, Dict, Any

load_dotenv()
API_KEY = os.getenv("API_KEY")
CACHE_FILE = "weather_cache.json"


def request_with_retries(url: str, max_retries: int = 3) -> Optional[requests.Response]:
    """HTTP-запрос с ретраями и экспоненциальной паузой при временных ошибках."""
    backoff = 1
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=10)
            # 429 или временные ошибки 5xx — пытаемся повторить
            if response.status_code == 429 or 500 <= response.status_code < 600:
                print(f"Временная ошибка ({response.status_code}), попытка {attempt} из {max_retries}")
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
            return response
        except requests.RequestException as e:
            print(f"Сетевая ошибка: {e}, попытка {attempt} из {max_retries}")
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            return None
    return None


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
    # если сохранённое время без таймзоны, считаем его UTC
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


def get_current_weather(city: str = None, latitude: float = None, longitude: float = None) -> Optional[dict]:
    if city:
        print(f"Получаем погоду для города - {city}")
        coords = get_coordinates(city)
        if coords is None:
            print("Не удалось получить координаты города")
            return None
        latitude, longitude = coords
        return get_weather_by_coordinates(latitude, longitude)
    
    if latitude is not None and longitude is not None:
        print(f"Получаем погоду для координат - {latitude}, {longitude}")
        return get_weather_by_coordinates(latitude, longitude)

def get_coordinates(city: str) -> Optional[Tuple[float, float]]:
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}"
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос для получения координат.")
        return None
    if response.status_code == 200:
        data = response.json()
        if not data:
            print("Город не найден.")
            return None
        return data[0]["lat"], data[0]["lon"]
    else:
        print(f"Не удалось получить координаты города: {response.status_code}")
        return None
    
def get_weather_by_coordinates(latitude: float, longitude: float) -> Optional[dict]:
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    )
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос погоды.")
        # Попробуем предложить данные из кэша
        cache = load_cache()
        if cache and is_cache_fresh(cache):
            choice = input("Использовать данные из кэша (меньше 3 часов)? (y/n): ").strip().lower()
            if choice == "y":
                return cache.get("weather")
        return None

    if response.status_code == 200:
        weather = response.json()
        cache_weather(weather.get("name"), latitude, longitude, weather)
        return weather
    else:
        print(f"Ошибка: {response.status_code}")
        return None


if __name__ == "__main__":
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        exit(1)

    while True:
        print("\nВыберите режим:")
        print("1 — по городу")
        print("2 — по координатам")
        print("0 — выход")
        mode = input("Введите номер операции: ").strip()

        if mode == "0":
            print("Выход.")
            break

        if mode == "1":
            city = input("Введите название города: ").strip()
            if not city:
                print("Город не может быть пустым.")
                continue
            weather = get_current_weather(city=city)
        elif mode == "2":
            try:
                lat_str = input("Введите широту: ").strip()
                lon_str = input("Введите долготу: ").strip()
                latitude = float(lat_str)
                longitude = float(lon_str)
            except ValueError:
                print("Неверный формат координат.")
                continue
            weather = get_current_weather(latitude=latitude, longitude=longitude)
        else:
            print("Неизвестный режим. Повторите ввод.")
            continue

        if weather is None:
            print("Не удалось получить данные о погоде.")
            continue

        try:
            print(
                f"Погода в городе - {weather['name']}: "
                f"{weather['main']['temp']}°C, {weather['weather'][0]['description']}"
            )
        except (KeyError, TypeError):
            print("Получен неожиданный формат ответа от API:")
            print(weather)