import telebot
import os
import schedule
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from telebot import types

from src.api_client import (
    get_coordinates,
    get_weather_by_coordinates,
    get_hourly_weather,
    get_air_pollution,
    get_current_weather
)
from src.storage import load_bot_users, save_bot_users

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не установлен.")
    raise SystemExit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище данных пользователей
user_data = load_bot_users()


# ============================================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================================

def get_main_keyboard():
    """Главная inline-клавиатура с фиксированной шириной кнопок."""
    # Используем неразрывные пробелы (U+00A0) для выравнивания ширины кнопок
    nbsp = '\u00A0'  # Неразрывный пробел
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(f"☀️ Текущая погода{nbsp * 6}", callback_data="menu_weather"),
        types.InlineKeyboardButton(f"📅 Прогноз на 5 дней{nbsp * 3}", callback_data="menu_forecast")
    )
    keyboard.row(
        types.InlineKeyboardButton("📍 Отправить местоположение", callback_data="menu_location"),
        types.InlineKeyboardButton(f"🔔 Уведомления{nbsp * 9}", callback_data="menu_notifications")
    )
    keyboard.row(
        types.InlineKeyboardButton(f"⚖️ Сравнить города{nbsp * 5}", callback_data="menu_compare"),
        types.InlineKeyboardButton(f"📊 Расширенные данные{nbsp * 2}", callback_data="menu_extended")
    )
    return keyboard


@bot.message_handler(commands=['start', 'help', 'menu'])
def send_welcome(message):
    """Обработчик команд /start, /help и /menu."""
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {
            "location": None,
            "notifications": False,
            "last_weather": None
        }
        save_bot_users(user_data)
    
    welcome_text = (
        "☀️ *Добро пожаловать в WeatherBot!*\n\n"
        "Я помогу вам получить актуальную информацию о погоде:\n\n"
        "🌡 Текущая погода в любом городе\n"
        "📅 Прогноз на 5 дней вперед\n"
        "📍 Погода по вашему местоположению\n"
        "🔔 Погодные уведомления\n"
        "⚖️ Сравнение погоды в разных городах\n"
        "📊 Расширенная информация о погоде\n\n"
        "Выберите действие:"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# ============================================================================
# ОБРАБОТЧИКИ INLINE-КНОПОК ГЛАВНОГО МЕНЮ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_weather")
def request_current_weather_callback(call):
    """Запрос текущей погоды через callback."""
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "Введите название города:"
    )
    bot.register_next_step_handler(msg, show_current_weather)


# ============================================================================
# 1. ТЕКУЩАЯ ПОГОДА ПО ГОРОДУ
# ============================================================================


def show_current_weather(message):
    """Показать текущую погоду."""
    city = message.text.strip()
    
    # Проверка на пустой ввод
    if not city:
        bot.send_message(
            message.chat.id,
            "❌ Название города не может быть пустым. Попробуйте еще раз."
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    bot.send_message(message.chat.id, "⏳ Получаю данные...")
    
    weather = get_current_weather(city=city)
    
    if not weather:
        bot.send_message(
            message.chat.id,
            f"❌ Город '{city}' не найден.\n\n"
            f"Попробуйте:\n"
            f"• Проверить правильность написания\n"
            f"• Использовать английское название\n"
            f"• Отправить местоположение вместо названия"
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    if isinstance(weather, list):
        # Несколько вариантов городов
        for entry in weather:
            location = entry.get("location", {})
            weather_data = entry.get("weather")
            if weather_data:
                text = format_current_weather(weather_data, location)
                bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        text = format_current_weather(weather)
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
    # Показываем меню снова
    bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


def format_current_weather(weather: Dict, location: Optional[Dict] = None) -> str:
    """Форматировать данные текущей погоды."""
    try:
        # Используем только название города без региона
        city_name = weather.get("name", "Неизвестный город")
        if location and location.get("name"):
            city_name = location.get("name")
        
        temp = weather["main"]["temp"]
        feels_like = weather["main"]["feels_like"]
        description = weather["weather"][0]["description"].capitalize()
        humidity = weather["main"]["humidity"]
        wind_speed = weather["wind"]["speed"]
        pressure = weather["main"]["pressure"]
        
        text = (
            f"🌤 *Погода в городе {city_name}*\n\n"
            f"🌡 Температура: *{temp}°C*\n"
            f"🤔 Ощущается как: *{feels_like}°C*\n"
            f"📝 Описание: {description}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind_speed} м/с\n"
            f"🔽 Давление: {pressure} гПа\n"
        )
        
        return text
    except (KeyError, TypeError) as e:
        return f"❌ Ошибка обработки данных: {e}"


# ============================================================================
# 2. ПРОГНОЗ НА 5 ДНЕЙ С INLINE-КЛАВИАТУРОЙ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_forecast")
def request_forecast_callback(call):
    """Запрос прогноза на 5 дней через callback."""
    bot.answer_callback_query(call.id)
    request_forecast(call.message, call.message.chat.id)


def request_forecast(message, chat_id=None):
    """Запрос прогноза на 5 дней."""
    if chat_id is None:
        chat_id = message.chat.id
    
    user_id = str(chat_id)
    
    if user_id not in user_data or not user_data[user_id].get("location"):
        bot.send_message(
            chat_id,
            "❌ Сначала отправьте ваше местоположение.\n\n"
            "Нажмите кнопку '📍 Отправить местоположение' в меню ниже."
        )
        bot.send_message(
            chat_id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    location = user_data[user_id]["location"]
    lat, lon = location["lat"], location["lon"]
    
    bot.send_message(chat_id, "⏳ Получаю прогноз...")
    
    forecast = get_hourly_weather(lat, lon)
    
    if not forecast:
        bot.send_message(
            chat_id,
            "❌ Не удалось получить прогноз погоды."
        )
        return
    
    show_forecast_days(chat_id, forecast)


def show_forecast_days(chat_id: int, forecast: Dict, message_id: Optional[int] = None):
    """Показать дни прогноза."""
    forecast_list = forecast.get("list", [])
    if not forecast_list:
        bot.send_message(chat_id, "❌ Нет данных прогноза")
        return
    
    # Группируем по дням
    days = {}
    for item in forecast_list:
        date = item["dt_txt"].split()[0]
        if date not in days:
            days[date] = []
        days[date].append(item)
    
    # Создаем inline-клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for date in sorted(days.keys())[:5]:
        # Получаем средние значения за день
        temps = [item["main"]["temp"] for item in days[date]]
        avg_temp = sum(temps) / len(temps)
        
        # Форматируем дату
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%d.%m")
        
        button_text = f"{date_str} ({avg_temp:.1f}°C)"
        buttons.append(types.InlineKeyboardButton(
            button_text,
            callback_data=f"day_{date}"
        ))
    
    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton("🔙 Закрыть", callback_data="close"))
    
    city_name = forecast.get("city", {}).get("name", "Ваше местоположение")
    text = f"📅 *Прогноз на 5 дней для {city_name}*\n\nВыберите день:"
    
    if message_id:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        bot.send_message(
            chat_id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("day_"))
def show_day_details(call):
    """Показать детали дня."""
    date = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    
    if user_id not in user_data or not user_data[user_id].get("location"):
        bot.answer_callback_query(call.id, "❌ Местоположение не сохранено")
        return
    
    location = user_data[user_id]["location"]
    forecast = get_hourly_weather(location["lat"], location["lon"])
    
    if not forecast:
        bot.answer_callback_query(call.id, "❌ Ошибка получения данных")
        return
    
    # Фильтруем данные по дню
    forecast_list = forecast.get("list", [])
    day_data = [item for item in forecast_list if item["dt_txt"].startswith(date)]
    
    if not day_data:
        bot.answer_callback_query(call.id, "❌ Нет данных")
        return
    
    # Форматируем детали
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    date_str = date_obj.strftime("%d %B %Y")
    
    text = f"📅 *{date_str}*\n\n"
    
    for item in day_data:
        time_str = item["dt_txt"].split()[1][:5]
        temp = item["main"]["temp"]
        description = item["weather"][0]["description"]
        humidity = item["main"]["humidity"]
        wind = item["wind"]["speed"]
        
        text += (
            f"🕐 *{time_str}*\n"
            f"🌡 {temp}°C, {description}\n"
            f"💧 {humidity}%, 💨 {wind} м/с\n\n"
        )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_days"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_days")
def back_to_days(call):
    """Вернуться к списку дней."""
    user_id = str(call.from_user.id)
    
    if user_id not in user_data or not user_data[user_id].get("location"):
        bot.answer_callback_query(call.id, "❌ Местоположение не сохранено")
        return
    
    location = user_data[user_id]["location"]
    forecast = get_hourly_weather(location["lat"], location["lon"])
    
    if forecast:
        show_forecast_days(
            call.message.chat.id,
            forecast,
            call.message.message_id
        )
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "close")
def close_inline(call):
    """Закрыть inline-сообщение."""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


# ============================================================================
# 3. ПОИСК ПО ГЕОЛОКАЦИИ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_location")
def request_location_callback(call):
    """Запрос отправки местоположения."""
    bot.answer_callback_query(call.id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📍 Отправить местоположение", request_location=True))
    bot.send_message(
        call.message.chat.id,
        "Нажмите кнопку ниже, чтобы отправить ваше местоположение:",
        reply_markup=keyboard
    )


@bot.message_handler(content_types=['location'])
def handle_location(message):
    """Обработка геолокации."""
    user_id = str(message.from_user.id)
    
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    # Проверяем, для чего отправлена геолокация
    if user_id in user_data and user_data[user_id].get("waiting_for_extended"):
        # Расширенные данные
        user_data[user_id]["waiting_for_extended"] = False
        save_bot_users(user_data)
        
        bot.send_message(message.chat.id, "⏳ Получаю данные...")
        show_extended_data(message.chat.id, latitude, longitude)
        return
    
    # Сохраняем координаты
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]["location"] = {
        "lat": latitude,
        "lon": longitude
    }
    save_bot_users(user_data)
    
    bot.send_message(
        message.chat.id,
        f"✅ Местоположение сохранено!\n📍 Координаты: {latitude:.4f}, {longitude:.4f}\n\n⏳ Получаю погоду..."
    )
    
    # Показываем погоду
    weather = get_weather_by_coordinates(latitude, longitude)
    
    if weather:
        text = format_current_weather(weather)
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Не удалось получить погоду")
    
    bot.send_message(
        message.chat.id,
        "Теперь вы можете использовать 'Прогноз на 5 дней'! 📅\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )


# ============================================================================
# 4. ПОГОДНЫЕ УВЕДОМЛЕНИЯ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_notifications")
def notifications_menu_callback(call):
    """Меню уведомлений через callback."""
    bot.answer_callback_query(call.id)
    notifications_menu(call.message, call.message.chat.id)


def notifications_menu(message, chat_id=None):
    """Меню уведомлений."""
    if chat_id is None:
        chat_id = message.chat.id
    
    user_id = str(chat_id)
    
    if user_id not in user_data:
        user_data[user_id] = {"notifications": False, "location": None}
        save_bot_users(user_data)
    
    status = "✅ Включены" if user_data[user_id].get("notifications") else "❌ Выключены"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "✅ Включить" if not user_data[user_id].get("notifications") else "❌ Выключить",
            callback_data="toggle_notifications"
        )
    )
    
    text = (
        f"🔔 *Погодные уведомления*\n\n"
        f"Статус: {status}\n\n"
        f"При включении вы будете получать уведомления каждые 2 часа, "
        f"если ожидаются изменения погоды.\n\n"
        f"⚠️ Для уведомлений необходимо сохранить местоположение!"
    )
    
    bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "toggle_notifications")
def toggle_notifications(call):
    """Переключить уведомления."""
    user_id = str(call.from_user.id)
    
    if user_id not in user_data:
        user_data[user_id] = {"notifications": False, "location": None}
    
    if not user_data[user_id].get("location"):
        bot.answer_callback_query(
            call.id,
            "❌ Сначала отправьте местоположение!",
            show_alert=True
        )
        return
    
    # Переключаем
    user_data[user_id]["notifications"] = not user_data[user_id].get("notifications", False)
    save_bot_users(user_data)
    
    status = "включены" if user_data[user_id]["notifications"] else "выключены"
    
    bot.answer_callback_query(call.id, f"✅ Уведомления {status}")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        f"🔔 Уведомления {status}!\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )


def check_weather_notifications():
    """Проверка погоды для уведомлений (каждые 2 часа)."""
    for user_id, data in user_data.items():
        if not data.get("notifications") or not data.get("location"):
            continue
        
        try:
            location = data["location"]
            weather = get_weather_by_coordinates(location["lat"], location["lon"])
            
            if not weather:
                continue
            
            # Получаем прогноз
            forecast = get_hourly_weather(location["lat"], location["lon"])
            
            if forecast and forecast.get("list"):
                # Проверяем ближайшие часы на дождь/снег
                next_hours = forecast["list"][:4]  # 12 часов вперед
                
                has_rain = any("rain" in item.get("weather", [{}])[0].get("main", "").lower() 
                              for item in next_hours)
                has_snow = any("snow" in item.get("weather", [{}])[0].get("main", "").lower() 
                              for item in next_hours)
                
                message = None
                
                if has_rain:
                    message = "🌧 *Внимание!*\nВ ближайшие 12 часов ожидается дождь. Возьмите зонт!"
                elif has_snow:
                    message = "❄️ *Внимание!*\nВ ближайшие 12 часов ожидается снег. Одевайтесь теплее!"
                
                if message:
                    temp = weather["main"]["temp"]
                    message += f"\n\n🌡 Текущая температура: {temp}°C"
                    
                    bot.send_message(
                        int(user_id),
                        message,
                        parse_mode="Markdown"
                    )
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")


def run_scheduler():
    """Запуск планировщика."""
    schedule.every(2).hours.do(check_weather_notifications)
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================================
# 5. СРАВНЕНИЕ ГОРОДОВ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_compare")
def request_compare_cities_callback(call):
    """Запрос сравнения городов через callback."""
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "Введите два города через запятую\nНапример: *Москва, Санкт-Петербург*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, compare_cities)


def compare_cities(message):
    """Сравнить погоду в двух городах."""
    text = message.text.strip()
    
    # Проверка на пустой ввод
    if not text or "," not in text:
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат!\n\n"
            "Введите два города через запятую.\n"
            "Например: Москва, Санкт-Петербург"
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    cities = [city.strip() for city in text.split(",")]
    
    if len(cities) != 2 or not cities[0] or not cities[1]:
        bot.send_message(
            message.chat.id,
            "❌ Необходимо ввести ровно два города через запятую!\n\n"
            "Пример: Москва, Санкт-Петербург"
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    bot.send_message(message.chat.id, "⏳ Получаю данные...")
    
    weather1 = get_current_weather(city=cities[0])
    weather2 = get_current_weather(city=cities[1])
    
    if not weather1 or not weather2:
        bot.send_message(
            message.chat.id,
            "❌ Не удалось получить данные. Проверьте названия городов."
        )
        return
    
    # Берем первый вариант если список
    w1 = weather1[0]["weather"] if isinstance(weather1, list) else weather1
    w2 = weather2[0]["weather"] if isinstance(weather2, list) else weather2
    
    text = format_comparison(cities[0], w1, cities[1], w2)
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )
    
    bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


def format_comparison(city1: str, w1: Dict, city2: str, w2: Dict) -> str:
    """Форматировать сравнение городов."""
    try:
        temp1 = w1["main"]["temp"]
        temp2 = w2["main"]["temp"]
        
        text = f"⚖️ *Сравнение погоды*\n\n"
        text += f"```\n"
        text += f"{'Параметр':<20} {city1[:10]:<12} {city2[:10]:<12}\n"
        text += f"{'-'*44}\n"
        text += f"{'Температура':<20} {temp1:>6.1f}°C    {temp2:>6.1f}°C\n"
        text += f"{'Ощущается':<20} {w1['main']['feels_like']:>6.1f}°C    {w2['main']['feels_like']:>6.1f}°C\n"
        text += f"{'Влажность':<20} {w1['main']['humidity']:>6}%      {w2['main']['humidity']:>6}%\n"
        text += f"{'Ветер':<20} {w1['wind']['speed']:>6.1f} м/с  {w2['wind']['speed']:>6.1f} м/с\n"
        text += f"{'Давление':<20} {w1['main']['pressure']:>6} гПа  {w2['main']['pressure']:>6} гПа\n"
        text += f"```\n"
        
        diff = abs(temp1 - temp2)
        warmer = city1 if temp1 > temp2 else city2
        text += f"\n🌡 В городе *{warmer}* теплее на *{diff:.1f}°C*"
        
        return text
    except (KeyError, TypeError) as e:
        return f"❌ Ошибка обработки данных: {e}"


# ============================================================================
# 6. РАСШИРЕННЫЕ ДАННЫЕ
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_extended")
def request_extended_data_callback(call):
    """Запрос расширенных данных через callback."""
    bot.answer_callback_query(call.id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("По городу", callback_data="extended_city"),
        types.InlineKeyboardButton("По геолокации", callback_data="extended_location")
    )
    
    bot.send_message(
        call.message.chat.id,
        "Выберите способ поиска:",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "extended_city")
def request_extended_city(call):
    """Запрос города для расширенных данных."""
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "Введите название города:"
    )
    bot.register_next_step_handler(msg, show_extended_by_city)


@bot.callback_query_handler(func=lambda call: call.data == "extended_location")
def request_extended_location(call):
    """Запрос местоположения для расширенных данных."""
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    
    # Устанавливаем флаг, что ждем геолокацию для расширенных данных
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["waiting_for_extended"] = True
    save_bot_users(user_data)
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📍 Отправить местоположение", request_location=True))
    bot.send_message(
        call.message.chat.id,
        "Нажмите кнопку ниже, чтобы отправить ваше местоположение:",
        reply_markup=keyboard
    )


def show_extended_by_city(message):
    """Показать расширенные данные по городу."""
    city = message.text.strip()
    
    bot.send_message(message.chat.id, "⏳ Получаю данные...")
    
    locations = get_coordinates(city)
    if not locations:
        bot.send_message(
            message.chat.id,
            "❌ Город не найден"
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
    
    location = locations[0]
    show_extended_data(message.chat.id, location["lat"], location["lon"], city)


def show_extended_data(chat_id: int, lat: float, lon: float, city_name: str = None):
    """Показать все расширенные данные."""
    weather = get_weather_by_coordinates(lat, lon)
    pollution = get_air_pollution(lat, lon)
    
    if not weather:
        bot.send_message(chat_id, "❌ Не удалось получить данные о погоде")
        return
    
    text = f"📊 *Расширенные данные*\n"
    if city_name:
        text += f"📍 {city_name}\n"
    text += f"🗺 {lat:.4f}, {lon:.4f}\n\n"
    
    # Основная погода
    text += f"🌤 *ПОГОДА*\n"
    text += f"🌡 Температура: {weather['main']['temp']}°C\n"
    text += f"🤔 Ощущается: {weather['main']['feels_like']}°C\n"
    text += f"📝 {weather['weather'][0]['description'].capitalize()}\n"
    text += f"💧 Влажность: {weather['main']['humidity']}%\n"
    text += f"💨 Ветер: {weather['wind']['speed']} м/с\n"
    text += f"🔽 Давление: {weather['main']['pressure']} гПа\n"
    text += f"☁️ Облачность: {weather['clouds']['all']}%\n"
    text += f"👁 Видимость: {weather.get('visibility', 'N/A')} м\n"
    
    # Восход/закат
    if 'sys' in weather:
        sunrise = datetime.fromtimestamp(weather['sys']['sunrise']).strftime('%H:%M')
        sunset = datetime.fromtimestamp(weather['sys']['sunset']).strftime('%H:%M')
        text += f"🌅 Восход: {sunrise}\n"
        text += f"🌇 Закат: {sunset}\n"
    
    # Качество воздуха
    if pollution and pollution.get("list"):
        text += f"\n🌫 *КАЧЕСТВО ВОЗДУХА*\n"
        aqi = pollution["list"][0]["main"]["aqi"]
        aqi_names = {1: "Отличное", 2: "Хорошее", 3: "Умеренное", 4: "Плохое", 5: "Очень плохое"}
        text += f"📊 AQI: {aqi} - {aqi_names.get(aqi, 'N/A')}\n"
        
        components = pollution["list"][0]["components"]
        text += f"CO: {components.get('co', 'N/A')} мкг/м³\n"
        text += f"NO₂: {components.get('no2', 'N/A')} мкг/м³\n"
        text += f"O₃: {components.get('o3', 'N/A')} мкг/м³\n"
        text += f"PM2.5: {components.get('pm2_5', 'N/A')} мкг/м³\n"
        text += f"PM10: {components.get('pm10', 'N/A')} мкг/м³\n"
    
    bot.send_message(chat_id, text, parse_mode="Markdown")
    bot.send_message(
        chat_id,
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


# ============================================================================
# INLINE-РЕЖИМ
# ============================================================================

@bot.inline_handler(lambda query: len(query.query) > 0)
def inline_query_handler(query):
    """Обработчик inline-запросов."""
    city = query.query.strip()
    
    if not city:
        return
    
    try:
        # Получаем погоду
        weather = get_current_weather(city=city)
        
        if not weather:
            # Город не найден
            result = types.InlineQueryResultArticle(
                id='1',
                title=f'Город "{city}" не найден',
                description='Проверьте правильность написания',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"❌ Город '{city}' не найден"
                )
            )
            bot.answer_inline_query(query.id, [result], cache_time=60)
            return
        
        results = []
        
        if isinstance(weather, list):
            # Несколько вариантов городов
            for idx, entry in enumerate(weather[:5]):  # Максимум 5 результатов
                location = entry.get("location", {})
                weather_data = entry.get("weather")
                
                if not weather_data:
                    continue
                
                city_name = location.get("name", "Неизвестный город")
                temp = weather_data["main"]["temp"]
                description = weather_data["weather"][0]["description"]
                humidity = weather_data["main"]["humidity"]
                wind = weather_data["wind"]["speed"]
                
                message_text = (
                    f"🌤 *{city_name}*\n\n"
                    f"🌡 Температура: *{temp}°C*\n"
                    f"📝 {description.capitalize()}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind} м/с"
                )
                
                result = types.InlineQueryResultArticle(
                    id=str(idx),
                    title=f'{city_name}: {temp}°C',
                    description=f'{description.capitalize()}, влажность {humidity}%',
                    thumbnail_url='https://openweathermap.org/img/wn/01d@2x.png',
                    input_message_content=types.InputTextMessageContent(
                        message_text=message_text,
                        parse_mode='Markdown'
                    )
                )
                results.append(result)
        else:
            # Один результат
            city_name = weather.get("name", city)
            temp = weather["main"]["temp"]
            description = weather["weather"][0]["description"]
            humidity = weather["main"]["humidity"]
            wind = weather["wind"]["speed"]
            
            message_text = (
                f"🌤 *{city_name}*\n\n"
                f"🌡 Температура: *{temp}°C*\n"
                f"📝 {description.capitalize()}\n"
                f"💧 Влажность: {humidity}%\n"
                f"💨 Ветер: {wind} м/с"
            )
            
            result = types.InlineQueryResultArticle(
                id='1',
                title=f'{city_name}: {temp}°C',
                description=f'{description.capitalize()}, влажность {humidity}%',
                thumbnail_url='https://openweathermap.org/img/wn/01d@2x.png',
                input_message_content=types.InputTextMessageContent(
                    message_text=message_text,
                    parse_mode='Markdown'
                )
            )
            results.append(result)
        
        bot.answer_inline_query(query.id, results, cache_time=600)
    
    except Exception as e:
        print(f"Ошибка в inline-режиме: {e}")
        result = types.InlineQueryResultArticle(
            id='1',
            title='Ошибка',
            description='Не удалось получить данные о погоде',
            input_message_content=types.InputTextMessageContent(
                message_text="❌ Не удалось получить данные о погоде"
            )
        )
        bot.answer_inline_query(query.id, [result], cache_time=60)


# ============================================================================
# ЗАПУСК БОТА
# ============================================================================

def main():
    """Главная функция запуска бота."""
    print("🤖 Бот запущен!")
    print("📍 Inline-режим активен")
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Запускаем бота
    bot.infinity_polling()


if __name__ == "__main__":
    main()