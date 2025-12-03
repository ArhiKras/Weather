"""
CLI приложение для получения информации о погоде.
Поддерживает получение данных по городу и координатам.
"""

from src.api_client import API_KEY
from src.CLI import run_cli

def main():
    if not API_KEY:
        print("Ошибка: API_KEY не найден в файле .env")
        return
    
    run_cli()

if __name__ == "__main__":
    main()

