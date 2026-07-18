import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTERS_CHAT_ID = int(os.getenv("MASTERS_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ORDERS_DB = {}
order_counter = 1

# --- Состояния ---
class OrderSteps(StatesGroup):
    choosing_service = State()
    entering_area = State()

class MasterSteps(StatesGroup):
    waiting_for_price = State()

# --- Хендлеры ---
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text="Шкаф 🗄", callback_data="service_шкаф")],
        [InlineKeyboardButton(text="Кровать 🛏", callback_data="service_кровать")]
    ]
    await message.answer("Что нужно собрать?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(OrderSteps.choosing_service)

@dp.callback_query(OrderSteps.choosing_service, F.data.startswith("service_"))
async def service_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(service=callback.data.split("_")[1])
    await callback.message.answer("Укажите район:")
    await state.set_state(OrderSteps.entering_area)
    await callback.answer()

@dp.message(OrderSteps.entering_area)
async def area_entered(message: Message, state: FSMContext):
    global order_counter
    data = await state.get_data()
    order_id = order_counter
    ORDERS_DB[order_id] = {"client_chat_id": message.chat.id, "details": f"Заявка №{order_id}\nУслуга: {data['service']}\nРайон: {message.text}"}
    order_counter += 1
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Взять заказ", callback_data=f"take_{order_id}")]])
    await bot.send_message(MASTERS_CHAT_ID, text=ORDERS_DB[order_id]["details"], reply_markup=keyboard)
    await message.answer("Заявка передана!")
    await state.clear()

@dp.callback_query(F.data.startswith("take_"))
async def master_take(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await callback.message.edit_text(text=f"{callback.message.text}\n\n🛑 ЗАЯВКА ВЗЯТА: @{callback.from_user.username}", reply_markup=None)
    await bot.send_message(callback.from_user.id, f"Заказ №{order_id}. Напишите цену и время.")
    await state.set_state(MasterSteps.waiting_for_price)
    await state.update_data(order_id=order_id)
    await callback.answer()

@dp.message(MasterSteps.waiting_for_price)
async def process_master_price(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    client_id = ORDERS_DB[order_id]["client_chat_id"]
    await bot.send_message(client_id, f"👔 Ответ мастера по заявке №{order_id}:\n{message.text}")
    await message.answer("✅ Отправлено!")
    await state.clear()

# --- Настройка вебхука ---
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

def main():
    app = web.Application()
    
    # Регистрация обработчика на корень
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path="/")
    
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()