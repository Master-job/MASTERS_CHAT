import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import load_config
from bot.database import Database
from bot.handlers import client, master

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def health_check(request: web.Request) -> web.Response:
    """Простой эндпоинт для аптайм-мониторов и health checks у хостинга."""
    return web.Response(text="OK")


def main() -> None:
    config = load_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(client.router)
    dp.include_router(master.router)

    db = Database(config.db_path)

    # DI: aiogram сам подставит db / masters_chat_id в хендлеры по имени параметра.
    dp["db"] = db
    dp["masters_chat_id"] = config.masters_chat_id

    app = web.Application()
    app.router.add_get("/", health_check)

    async def on_startup(app: web.Application) -> None:
        await db.connect()
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(
            config.webhook_url,
            secret_token=config.webhook_secret or None,
            allowed_updates=["message", "callback_query"],
        )
        logger.info("Webhook установлен: %s", config.webhook_url)

    async def on_shutdown(app: web.Application) -> None:
        await db.close()
        await bot.session.close()
        logger.info("Бот остановлен, соединения закрыты.")

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.webhook_secret or None,
    )
    handler.register(app, path=config.webhook_path)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)

    web.run_app(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
