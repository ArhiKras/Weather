from api_client import API_KEY
from cli import run_cli


def main() -> None:
    if not API_KEY:
        print("Ошибка: переменная окружения API_KEY не установлена.")
        raise SystemExit(1)

    run_cli()


if __name__ == "__main__":
    main()