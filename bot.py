import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTERS_CHAT_ID = int(os.getenv("MASTERS_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ORDERS_DB = {}
order_counter = 1

# ... [Твои классы и хендлеры остаются без изменений, вставляй их сюда] ...

async def on_startup(app: web.Application):
    # Просто ставим вебхук на корень сервера
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

def main():
    app = web.Application()
    
    # Регистрация на корень "/" - это всегда работает
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path="/")
    
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()