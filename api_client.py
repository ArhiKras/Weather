import os
import time
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")


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


def get_coordinates(city: str, limit: int = 3) -> Optional[List[Dict[str, Any]]]:
    """Получить до `limit` вариантов города (одноимённые города в разных регионах)."""
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        return None

    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit={limit}&appid={API_KEY}"
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос для получения координат.")
        return None

    if response.status_code == 200:
        data = response.json()
        if not data:
            print("Город не найден.")
            return None

        locations: List[Dict[str, Any]] = []
        for item in data[:limit]:
            locations.append(
                {
                    "name": item.get("name"),
                    "state": item.get("state"),
                    "country": item.get("country"),
                    "lat": item["lat"],
                    "lon": item["lon"],
                }
            )
        return locations

    print(f"Не удалось получить координаты города: {response.status_code}")
    return None


def get_weather_by_coordinates(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Получить погоду по координатам (без кэширования, только HTTP-запрос)."""
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        return None

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    )
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос погоды.")
        return None

    if response.status_code == 200:
        return response.json()

    print(f"Ошибка при получении погоды: {response.status_code}")
    return None


