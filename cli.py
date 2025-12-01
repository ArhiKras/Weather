from typing import Optional, Any, Dict, List

from api_client import get_coordinates, get_weather_by_coordinates
from storage import load_cache, is_cache_fresh, cache_weather


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


def run_cli() -> None:
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

        if not weather:
            print("Не удалось получить данные о погоде.")
            continue

        if isinstance(weather, list):
            for entry in weather:
                location = entry.get("location", {})
                weather_data = entry.get("weather")
                if not weather_data:
                    continue
                region = location.get("state") or location.get("country") or "неизвестная область"
                city_name = location.get("name") or "неизвестный город"
                try:
                    print(
                        f"Погода в городе - {city_name} ({region}): "
                        f"{weather_data['main']['temp']}°C, {weather_data['weather'][0]['description']}"
                    )
                except (KeyError, TypeError):
                    print("Получен неожиданный формат ответа от API:")
                    print(weather_data)
            continue

        try:
            print(
                f"Погода в городе - {weather['name']}: "
                f"{weather['main']['temp']}°C, {weather['weather'][0]['description']}"
            )
        except (KeyError, TypeError):
            print("Получен неожиданный формат ответа от API:")
            print(weather)


