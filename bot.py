import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Загружаем настройки из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTERS_CHAT_ID = int(os.getenv("MASTERS_CHAT_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище (в памяти)
# { order_id: {"client_chat_id": 123, "details": "...", "master_id": None} }
ORDERS_DB = {}
order_counter = 1

# Состояния для клиента
class OrderSteps(StatesGroup):
    choosing_service = State()
    entering_area = State()

# Состояния для мастера (в личке)
class MasterSteps(StatesGroup):
    waiting_for_price = State()

# --- ЛОГИКА КЛИЕНТА ---
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text="Шкаф 🗄", callback_data="service_шкаф")],
        [InlineKeyboardButton(text="Кровать 🛏", callback_data="service_кровать")]
    ]
    await message.answer("Привет! Что нужно собрать?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(OrderSteps.choosing_service)

@dp.callback_query(OrderSteps.choosing_service, F.data.startswith("service_"))
async def service_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(service=callback.data.split("_")[1])
    await callback.message.answer("Укажите район:")
    await state.set_state(OrderSteps.entering_area)

@dp.message(OrderSteps.entering_area)
async def area_entered(message: Message, state: FSMContext):
    global order_counter
    data = await state.get_data()
    
    order_id = order_counter
    ORDERS_DB[order_id] = {
        "client_chat_id": message.chat.id,
        "details": f"Заявка №{order_id}\nУслуга: {data['service']}\nРайон: {message.text}"
    }
    order_counter += 1
    
    # Кнопка для мастеров
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Взять заказ", callback_data=f"take_{order_id}")]])
    
    await bot.send_message(MASTERS_CHAT_ID, text=ORDERS_DB[order_id]["details"], reply_markup=keyboard)
    await message.answer("Заявка передана мастерам!")
    await state.clear()

# --- ЛОГИКА МАСТЕРА ---
@dp.callback_query(F.data.startswith("take_"))
async def master_take(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    
    # Редактируем сообщение в группе
    new_text = f"{callback.message.text}\n\n🛑 ЗАЯВКА ВЗЯТА: @{callback.from_user.username}"
    await callback.message.edit_text(text=new_text, reply_markup=None)
    
    # Открываем диалог в личке
    await bot.send_message(callback.from_user.id, f"Принято! Заказ №{order_id}. Напишите цену и время для клиента.")
    await state.set_state(MasterSteps.waiting_for_price)
    await state.update_data(order_id=order_id)

@dp.message(MasterSteps.waiting_for_price)
async def process_master_price(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    
    # Шлем клиенту
    client_id = ORDERS_DB[order_id]["client_chat_id"]
    await bot.send_message(client_id, f"👔 Ответ мастера по заявке №{order_id}:\n{message.text}")
    
    await message.answer("✅ Отправлено клиенту!")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())