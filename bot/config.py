import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    masters_chat_id: int
    webhook_url: str
    webhook_path: str
    webhook_secret: str
    port: int
    db_path: str


def load_config() -> Config:
    """Читает и валидирует переменные окружения.

    Падает с понятной ошибкой на старте, а не через час работы в проде.
    """
    try:
        bot_token = os.environ["BOT_TOKEN"]
        masters_chat_id = int(os.environ["MASTERS_CHAT_ID"])
        webhook_url = os.environ["WEBHOOK_URL"]
    except KeyError as e:
        raise RuntimeError(f"Не задана обязательная переменная окружения: {e}") from e
    except ValueError as e:
        raise RuntimeError(f"MASTERS_CHAT_ID должен быть числом (ID чата): {e}") from e

    return Config(
        bot_token=bot_token,
        masters_chat_id=masters_chat_id,
        webhook_url=webhook_url,
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
        webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
        port=int(os.getenv("PORT", "10000")),
        db_path=os.getenv("DB_PATH", "orders.db"),
    )
