import os
import time
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv
from src.storage import load_cache, is_cache_fresh, cache_weather, load_api_cache, save_api_cache

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


def get_coordinates(city: str, limit: int = 1) -> Optional[List[Dict[str, Any]]]:
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
    """Получить погоду по координатам с API кэшированием (10 минут)."""
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        return None

    # Проверяем API кэш
    cached = load_api_cache(latitude, longitude, "weather")
    if cached:
        return cached

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    )
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос погоды.")
        return None

    if response.status_code == 200:
        data = response.json()
        # Сохраняем в API кэш
        save_api_cache(latitude, longitude, "weather", data)
        return data

    print(f"Ошибка при получении погоды: {response.status_code}")
    return None


def get_weather_with_cache(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Получить погоду с учётом кэша и предложения использовать старые данные при ошибке сети."""
    weather = get_weather_by_coordinates(latitude, longitude)
    if weather is None:
        cache = load_cache()
        if cache and is_cache_fresh(cache):
            choice = input("Не удалось получить свежие данные. Использовать данные из кэша (меньше 3 часов)? (y/n): ").strip().lower()
            if choice == "y":
                return cache.get("weather")
        return None

    cache_weather(weather.get("name"), latitude, longitude, weather)
    return weather


def get_hourly_weather(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Получить почасовой прогноз погоды на 5 дней с API кэшированием (10 минут)."""
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        return None

    # Проверяем API кэш
    cached = load_api_cache(latitude, longitude, "forecast")
    if cached:
        return cached

    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    )
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос почасового прогноза.")
        return None

    if response.status_code == 200:
        data = response.json()
        # Сохраняем в API кэш
        save_api_cache(latitude, longitude, "forecast", data)
        return data

    print(f"Ошибка при получении почасового прогноза: {response.status_code}")
    return None


def get_air_pollution(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Получить данные о загрязнении воздуха с API кэшированием (10 минут)."""
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        return None

    # Проверяем API кэш
    cached = load_api_cache(latitude, longitude, "air_pollution")
    if cached:
        return cached

    url = (
        "http://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={latitude}&lon={longitude}&appid={API_KEY}"
    )
    response = request_with_retries(url)
    if response is None:
        print("Не удалось выполнить запрос данных о загрязнении воздуха.")
        return None

    if response.status_code == 200:
        data = response.json()
        # Сохраняем в API кэш
        save_api_cache(latitude, longitude, "air_pollution", data)
        return data

    print(f"Ошибка при получении данных о загрязнении воздуха: {response.status_code}")
    return None


def get_current_weather(city: str = None, latitude: float = None, longitude: float = None) -> Optional[Any]:
    if city:
        print(f"Получаем погоду для города - {city}")
        locations = get_coordinates(city)
        if not locations:
            print("Не удалось получить координаты города")
            return None

        weather_results: List[Dict[str, Any]] = []
        for location in locations:
            lat = location["lat"]
            lon = location["lon"]
            weather = get_weather_with_cache(lat, lon)
            if weather:
                weather_results.append({"location": location, "weather": weather})
        return weather_results

    if latitude is not None and longitude is not None:
        print(f"Получаем погоду для координат - {latitude}, {longitude}")
        return get_weather_with_cache(latitude, longitude)

    print("Необходимо указать либо город, либо координаты.")
    return None

