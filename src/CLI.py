from typing import Dict, Any, Optional
from src.api_client import get_current_weather, get_hourly_weather, get_air_pollution


def display_forecast(forecast: Dict[str, Any], location: Optional[Dict[str, str]] = None) -> None:
    """Отобразить почасовой прогноз погоды с пагинацией."""
    try:
        city_name = forecast.get("city", {}).get("name", "Неизвестный город")
        if location:
            region = location.get("state") or location.get("country") or "неизвестная область"
            city_name = f"{location.get('name', city_name)} ({region})"
        
        print(f"\n{'='*60}")
        print(f"Прогноз погоды на 5 дней (каждые 3 часа): {city_name}")
        print(f"{'='*60}")
        
        forecast_list = forecast.get("list", [])
        if not forecast_list:
            print("Нет данных прогноза")
            return
        
        total = len(forecast_list)
        print(f"Всего доступно прогнозов: {total}")
        
        # Показываем по 10 записей за раз
        start_index = 0
        page_size = 10
        
        while start_index < total:
            end_index = min(start_index + page_size, total)
            
            print(f"\n{'='*60}")
            print(f"Показаны записи {start_index + 1}-{end_index} из {total}")
            print(f"{'='*60}")
            
            for item in forecast_list[start_index:end_index]:
                dt_txt = item.get("dt_txt", "")
                temp = item.get("main", {}).get("temp", "N/A")
                description = item.get("weather", [{}])[0].get("description", "N/A")
                humidity = item.get("main", {}).get("humidity", "N/A")
                wind_speed = item.get("wind", {}).get("speed", "N/A")
                
                print(f"\n{dt_txt}")
                print(f"  Температура: {temp}°C")
                print(f"  Описание: {description}")
                print(f"  Влажность: {humidity}%")
                print(f"  Скорость ветра: {wind_speed} м/с")
            
            start_index = end_index
            
            # Если есть еще данные, спрашиваем пользователя
            if start_index < total:
                remaining = total - start_index
                choice = input(f"\nПоказать еще {min(page_size, remaining)} записей? (да/нет): ").strip().lower()
                if choice not in ["да", "yes", "y", "д"]:
                    break
        
        print(f"\n{'='*60}")
    except (KeyError, TypeError, IndexError) as e:
        print(f"Ошибка при отображении прогноза: {e}")
        print(forecast)


def get_pollutant_level(value: float, pollutant_type: str) -> str:
    """Определить уровень качества для конкретного загрязняющего вещества."""
    if value == "N/A":
        return "Нет данных"
    
    # Диапазоны на основе стандартов качества воздуха
    thresholds = {
        "pm2_5": [(0, 12, "Отлично"), (12, 35, "Хорошо"), (35, 55, "Умеренно"), 
                  (55, 150, "Плохо"), (150, 250, "Очень плохо"), (250, float('inf'), "Опасно")],
        "pm10": [(0, 54, "Отлично"), (54, 154, "Хорошо"), (154, 254, "Умеренно"), 
                 (254, 354, "Плохо"), (354, 424, "Очень плохо"), (424, float('inf'), "Опасно")],
        "o3": [(0, 60, "Отлично"), (60, 120, "Хорошо"), (120, 180, "Умеренно"), 
               (180, 240, "Плохо"), (240, 380, "Очень плохо"), (380, float('inf'), "Опасно")],
        "no2": [(0, 40, "Отлично"), (40, 90, "Хорошо"), (90, 120, "Умеренно"), 
                (120, 230, "Плохо"), (230, 340, "Очень плохо"), (340, float('inf'), "Опасно")],
        "no": [(0, 40, "Отлично"), (40, 90, "Хорошо"), (90, 150, "Умеренно"), 
               (150, 280, "Плохо"), (280, 400, "Очень плохо"), (400, float('inf'), "Опасно")],
        "so2": [(0, 40, "Отлично"), (40, 80, "Хорошо"), (80, 380, "Умеренно"), 
                (380, 800, "Плохо"), (800, 1600, "Очень плохо"), (1600, float('inf'), "Опасно")],
        "co": [(0, 4400, "Отлично"), (4400, 9400, "Хорошо"), (9400, 12400, "Умеренно"), 
               (12400, 15400, "Плохо"), (15400, 30400, "Очень плохо"), (30400, float('inf'), "Опасно")],
        "nh3": [(0, 10, "Отлично"), (10, 50, "Хорошо"), (50, 100, "Умеренно"), 
                (100, 200, "Плохо"), (200, 400, "Очень плохо"), (400, float('inf'), "Опасно")]
    }
    
    if pollutant_type not in thresholds:
        return "Неизвестно"
    
    for min_val, max_val, level in thresholds[pollutant_type]:
        if min_val <= value < max_val:
            return level
    
    return "Неизвестно"


def display_air_pollution(pollution_data: Dict[str, Any], location: Optional[Dict[str, str]] = None) -> None:
    """Отобразить данные о загрязнении воздуха."""
    try:
        city_name = "Неизвестное местоположение"
        if location:
            region = location.get("state") or location.get("country") or "неизвестная область"
            city_name = f"{location.get('name', 'Неизвестный город')} ({region})"
        
        print(f"\n{'='*60}")
        print(f"Качество воздуха для: {city_name}")
        print(f"{'='*60}")
        
        data_list = pollution_data.get("list", [])
        if not data_list:
            print("Нет данных о качестве воздуха")
            return
        
        # Берём первую запись (текущие данные)
        current = data_list[0]
        aqi = current.get("main", {}).get("aqi", "N/A")
        components = current.get("components", {})
        
        # Расшифровка индекса качества воздуха
        aqi_descriptions = {
            1: "Отличное",
            2: "Хорошее",
            3: "Умеренное",
            4: "Плохое",
            5: "Очень плохое"
        }
        aqi_desc = aqi_descriptions.get(aqi, "Неизвестно")
        
        print(f"\nОбщий индекс качества воздуха (AQI): {aqi} — {aqi_desc}")
        print(f"\n{'='*60}")
        print(f"Загрязняющие вещества (концентрация и индекс качества):")
        print(f"{'='*60}")
        
        # Данные о загрязняющих веществах
        pollutants = [
            ("CO", "co", "Угарный газ"),
            ("NO", "no", "Оксид азота"),
            ("NO₂", "no2", "Диоксид азота"),
            ("O₃", "o3", "Озон"),
            ("SO₂", "so2", "Диоксид серы"),
            ("PM2.5", "pm2_5", "Мелкие частицы"),
            ("PM10", "pm10", "Крупные частицы"),
            ("NH₃", "nh3", "Аммиак")
        ]
        
        for symbol, key, name in pollutants:
            concentration = components.get(key, "N/A")
            if concentration != "N/A":
                level = get_pollutant_level(concentration, key)
                print(f"{symbol} ({name}): {concentration} мкг/м³ - {level}")
            else:
                print(f"{symbol} ({name}): N/A - Нет данных")
        
        print(f"\n{'='*60}")
    except (KeyError, TypeError, IndexError) as e:
        print(f"Ошибка при отображении данных о загрязнении воздуха: {e}")
        print(pollution_data)


def display_current_weather(weather: Any) -> None:
    """Отобразить текущую погоду."""
    if not weather:
        print("Не удалось получить данные о погоде.")
        return

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
    else:
        try:
            print(
                f"Погода в городе - {weather['name']}: "
                f"{weather['main']['temp']}°C, {weather['weather'][0]['description']}"
            )
        except (KeyError, TypeError):
            print("Получен неожиданный формат ответа от API:")
            print(weather)


def submenu_by_city() -> None:
    """Подменю для работы с городом."""
    from src.api_client import get_coordinates
    
    city = input("\nВведите название города: ").strip()
    if not city:
        print("Город не может быть пустым.")
        return
    
    while True:
        print(f"\n{'='*60}")
        print(f"Город: {city}")
        print(f"{'='*60}")
        print("1 — Текущая погода")
        print("2 — Прогноз на 5 дней (каждые 3 часа)")
        print("3 — Качество воздуха")
        print("0 — Назад")
        choice = input("Выберите действие: ").strip()
        
        if choice == "0":
            break
        
        # Получаем координаты города
        locations = get_coordinates(city)
        if not locations:
            print("Не удалось получить координаты города")
            continue
        
        location = locations[0]
        
        if choice == "1":
            weather = get_current_weather(city=city)
            display_current_weather(weather)
        elif choice == "2":
            forecast = get_hourly_weather(location["lat"], location["lon"])
            if forecast:
                display_forecast(forecast, location)
            else:
                print("Не удалось получить прогноз погоды.")
        elif choice == "3":
            pollution = get_air_pollution(location["lat"], location["lon"])
            if pollution:
                display_air_pollution(pollution, location)
            else:
                print("Не удалось получить данные о качестве воздуха.")
        else:
            print("Неизвестная команда. Повторите ввод.")


def submenu_by_coordinates() -> None:
    """Подменю для работы с координатами."""
    try:
        lat_str = input("\nВведите широту: ").strip()
        lon_str = input("Введите долготу: ").strip()
        latitude = float(lat_str)
        longitude = float(lon_str)
    except ValueError:
        print("Неверный формат координат.")
        return
    
    while True:
        print(f"\n{'='*60}")
        print(f"Координаты: {latitude}, {longitude}")
        print(f"{'='*60}")
        print("1 — Текущая погода")
        print("2 — Прогноз на 5 дней (каждые 3 часа)")
        print("3 — Качество воздуха")
        print("0 — Назад")
        choice = input("Выберите действие: ").strip()
        
        if choice == "0":
            break
        
        if choice == "1":
            weather = get_current_weather(latitude=latitude, longitude=longitude)
            display_current_weather(weather)
        elif choice == "2":
            forecast = get_hourly_weather(latitude, longitude)
            if forecast:
                display_forecast(forecast)
            else:
                print("Не удалось получить прогноз погоды.")
        elif choice == "3":
            pollution = get_air_pollution(latitude, longitude)
            if pollution:
                display_air_pollution(pollution)
            else:
                print("Не удалось получить данные о качестве воздуха.")
        else:
            print("Неизвестная команда. Повторите ввод.")


def run_cli() -> None:
    """Главное меню приложения."""
    while True:
        print("\n" + "="*60)
        print("ПОГОДНОЕ ПРИЛОЖЕНИЕ")
        print("="*60)
        print("1 — Получить данные по городу")
        print("2 — Получить данные по координатам")
        print("0 — Выход")
        mode = input("Выберите режим: ").strip()

        if mode == "0":
            print("Выход.")
            break
        elif mode == "1":
            submenu_by_city()
        elif mode == "2":
            submenu_by_coordinates()
        else:
            print("Неизвестный режим. Повторите ввод.")


