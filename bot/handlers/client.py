from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from bot.states import OrderSteps
from bot.keyboards import services_keyboard, amount_keyboard, condition_keyboard, location_keyboard, timing_keyboard, confirm_keyboard

router = Router(name="client")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Как к вам обращаться?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderSteps.entering_name)

@router.message(OrderSteps.entering_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Шаг 1/6 — Что собираем?", reply_markup=services_keyboard())
    await state.set_state(OrderSteps.choosing_service)

@router.callback_query(OrderSteps.choosing_service)
async def get_service(call: CallbackQuery, state: FSMContext):
    await state.update_data(service=call.data.split("_")[1])
    await call.message.edit_text("Шаг 2/6 — Сколько изделий?", reply_markup=amount_keyboard())
    await state.set_state(OrderSteps.choosing_amount)

@router.callback_query(OrderSteps.choosing_amount)
async def get_amount(call: CallbackQuery, state: FSMContext):
    await state.update_data(amount=call.data.split("_")[1])
    await call.message.edit_text("Шаг 3/6 — Состояние мебели:", reply_markup=condition_keyboard())
    await state.set_state(OrderSteps.choosing_condition)

@router.callback_query(OrderSteps.choosing_condition)
async def get_cond(call: CallbackQuery, state: FSMContext):
    await state.update_data(condition=call.data.split("_")[1])
    await call.message.edit_text("Шаг 4/6 — Пришлите фото (или пропустите):")
    await state.set_state(OrderSteps.uploading_photo)

@router.message(OrderSteps.uploading_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Шаг 5/6 — Где адрес?", reply_markup=location_keyboard())
    await state.set_state(OrderSteps.choosing_location)

@router.callback_query(OrderSteps.choosing_location)
async def get_loc(call: CallbackQuery, state: FSMContext):
    await state.update_data(location=call.data.split("_")[1])
    await call.message.edit_text("Укажите район:")
    await state.set_state(OrderSteps.entering_district)

@router.message(OrderSteps.entering_district)
async def get_dist(message: Message, state: FSMContext):
    await state.update_data(district=message.text)
    await message.answer("Шаг 6/6 — Когда нужно?", reply_markup=timing_keyboard())
    await state.set_state(OrderSteps.choosing_timing)

@router.callback_query(OrderSteps.choosing_timing)
async def finish(call: CallbackQuery, state: FSMContext):
    await state.update_data(timing=call.data.split("_")[1])
    data = await state.get_data()
    # Отправляем готовую форму
    await call.message.answer(f"✅ Готово! Проверьте данные:\n\n{data}", reply_markup=confirm_keyboard())
    await state.set_state(OrderSteps.confirming)