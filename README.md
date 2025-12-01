## Weather CLI

Простое консольное приложение для получения погоды из OpenWeather по городу или координатам.

### Структура проекта

- `weather_app.py` — точка входа в приложение (проверка API ключа и запуск CLI).
- `api_client.py` — HTTP-запросы к API OpenWeather (геокодинг и погода).
- `storage.py` — кэширование и работа с локальным файлом `weather_cache.json`.
- `cli.py` — интерфейс командной строки и основная логика взаимодействия с пользователем.
- `requirements.txt` — зависимости проекта.
- `weather_cache.json` — файл с кэшированными ответами о погоде.

### Запуск

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создайте файл `.env` и добавьте в него API ключ OpenWeather:
   ```text
   API_KEY=ваш_ключ
   ```
3. Запустите приложение:
   ```bash
   python weather_app.py
   ```


