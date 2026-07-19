import logging
import re
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery

from bot.database import Database
from bot.formatting import format_order_card
from bot.keyboards import (
    MENU_CALC, MENU_CALL, MENU_EXAMPLES, MENU_FAQ, MENU_FAST, MENU_REVIEWS,
    booking_done_keyboard, contact_request_keyboard, date_keyboard,
    main_menu_keyboard, price_result_keyboard, quiz_keyboard,
    take_order_keyboard, time_slot_keyboard,
)
from bot.pricing import CONTACT_PHONE, EXAMPLES_TEXT, FAQ_TEXT, REVIEWS_TEXT, calculate_price
from bot.quiz_steps import get_steps
from bot.states import OrderSteps

logger = logging.getLogger(__name__)
router = Router(name="client")

PHONE_RE = re.compile(r"[\d+][\d\s\-()]{8,17}\d")
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# =====================================================================
# базовые команды и главное меню
# =====================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! 👋 Я бот по сборке корпусной мебели.\n\n"
        "Собираю шкафы, гардеробы, кровати, комоды и модульные гарнитуры — "
        "быстро и аккуратно. Все работы выполняют независимые мастера.\n\n"
        "Если нужно срочно и без вопросов — жмите «🛠 Заказать сборщика» 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📋 /start — открыть меню\n"
        "🚫 /cancel — отменить текущее оформление\n\n"
        "🧮 Рассчитать стоимость — квиз с ориентировочной ценой\n"
        "🛠 Заказать сборщика — без вопросов, мастер сам перезвонит"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Сейчас нечего отменять.")
        return
    await state.clear()
    await message.answer("Отменено. Открываю меню:", reply_markup=main_menu_keyboard())


@router.message(F.text == MENU_CALC)
async def menu_calc(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Давайте посчитаем стоимость. Это займёт меньше минуты.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(OrderSteps.quiz)
    await state.update_data(flow="full", step_index=0, answers={})
    await _ask_step(message, state)


@router.message(F.text == MENU_FAST)
async def menu_fast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Понял, без лишних вопросов.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderSteps.quiz)
    await state.update_data(flow="fast", step_index=0, answers={})
    await _ask_step(message, state)


@router.message(F.text == MENU_EXAMPLES)
async def menu_examples(message: Message) -> None:
    await message.answer(EXAMPLES_TEXT)


@router.message(F.text == MENU_REVIEWS)
async def menu_reviews(message: Message) -> None:
    await message.answer(REVIEWS_TEXT)


@router.message(F.text == MENU_FAQ)
async def menu_faq(message: Message) -> None:
    await message.answer(FAQ_TEXT)


@router.message(F.text == MENU_CALL)
async def menu_call(message: Message) -> None:
    await message.answer(f"📞 {CONTACT_PHONE}")


# =====================================================================
# движок квиза: один State, шаг определяется данными в FSMContext
# =====================================================================

async def _emit(target, text: str, keyboard=None, edit: bool = False) -> None:
    if edit:
        try:
            await target.edit_text(text, reply_markup=keyboard)
            return
        except Exception:
            pass
    await target.answer(text, reply_markup=keyboard)


async def _ask_step(target, state: FSMContext, edit: bool = False) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    idx = data["step_index"]
    step = steps[idx]

    await state.update_data(screen="quiz", awaiting="quiz_answer")
    await _emit(target, step.question, quiz_keyboard(step, idx), edit=edit)

    if step.kind == "phone":
        await target.answer(
            "Или отправьте контакт кнопкой ниже 👇", reply_markup=contact_request_keyboard()
        )


async def _advance(target, state: FSMContext, db: Database, masters_chat_id: int, edit: bool = False) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    next_idx = data["step_index"] + 1

    if next_idx >= len(steps):
        if data["flow"] == "fast":
            await _submit_order(target, state, db, masters_chat_id)
        else:
            await _show_price_result(target, state, edit=edit)
        return

    await state.update_data(step_index=next_idx)
    await _ask_step(target, state, edit=edit)


async def _show_price_result(target, state: FSMContext, edit: bool = False) -> None:
    data = await state.get_data()
    answers = data.get("answers", {})
    low, high = calculate_price(answers)
    answers["price_low"], answers["price_high"] = low, high
    await state.update_data(answers=answers, screen="result")

    card = format_order_card(
        order_id=None,
        name=answers.get("name", ""), phone=answers.get("phone", ""),
        service=answers.get("service"), volume=answers.get("volume"),
        demontage=answers.get("demontage"), hardware=answers.get("hardware"),
        district=answers.get("district"), timing=answers.get("timing"),
        price_low=low, price_high=high, order_date=None, time_slot=None,
    )
    text = (
        f"Готово! ✅\n\n{card}\n\n"
        "В стоимость входит выезд мастера по указанному району и сборка "
        "мебели. Точную смету мастер назовёт после фото/осмотра."
    )
    await _emit(target, text, price_result_keyboard(), edit=edit)


def _next_dates(n: int = 4):
    today = datetime.now()
    result = []
    for i in range(n):
        d = today + timedelta(days=i)
        if i == 0:
            label = "Сегодня"
        elif i == 1:
            label = "Завтра"
        else:
            label = f"{WEEKDAYS[d.weekday()]} {d.day}"
        result.append((d.strftime("%Y-%m-%d"), label))
    return result


async def _ask_date(target, state: FSMContext, edit: bool = False) -> None:
    dates = _next_dates()
    await state.update_data(screen="date", awaiting=None, date_options=dict(dates))
    await _emit(target, "Выберите дату приезда мастера:", date_keyboard(dates), edit=edit)


async def _ask_time(target, state: FSMContext, edit: bool = False) -> None:
    await state.update_data(screen="time", awaiting=None)
    await _emit(target, "Время приезда мастера:", time_slot_keyboard(), edit=edit)


async def _submit_order(
    target, state: FSMContext, db: Database, masters_chat_id: int,
    urgent: bool = False, scheduled: bool = False, to_manager: bool = False,
) -> None:
    data = await state.get_data()
    answers = data.get("answers", {})

    order_id = await db.create_order(
        client_chat_id=target.chat.id,
        urgent=urgent,
        service=answers.get("service"), volume=answers.get("volume"),
        demontage=answers.get("demontage"), hardware=answers.get("hardware"),
        district=answers.get("district"), timing=answers.get("timing"),
        photo_file_id=answers.get("photo"), name=answers.get("name"), phone=answers.get("phone"),
        price_low=answers.get("price_low"), price_high=answers.get("price_high"),
        order_date=answers.get("order_date") if scheduled else None,
        time_slot=answers.get("time_slot") if scheduled else None,
    )

    card = format_order_card(
        order_id=order_id,
        name=answers.get("name", ""), phone=answers.get("phone", ""),
        service=answers.get("service"), volume=answers.get("volume"),
        demontage=answers.get("demontage"), hardware=answers.get("hardware"),
        district=answers.get("district"), timing=answers.get("timing"),
        price_low=answers.get("price_low"), price_high=answers.get("price_high"),
        order_date=answers.get("order_date") if scheduled else None,
        time_slot=answers.get("time_slot") if scheduled else None,
        urgent=urgent,
    )

    photo_id = answers.get("photo")
    try:
        if photo_id:
            sent = await target.bot.send_photo(
                masters_chat_id, photo_id, caption=card, reply_markup=take_order_keyboard(order_id)
            )
        else:
            sent = await target.bot.send_message(
                masters_chat_id, card, reply_markup=take_order_keyboard(order_id)
            )
        await db.set_group_message(order_id, sent.chat.id, sent.message_id)
    except Exception:
        logger.exception("Не удалось отправить заявку №%s в чат мастеров", order_id)
        await target.answer("⚠️ Заявка сохранена, но не удалось передать её мастерам. Мы разберёмся.")
        await state.clear()
        return

    if to_manager:
        final_text = f"💬 Передал заявку №{order_id} менеджеру, скоро с вами свяжутся!"
    elif scheduled:
        final_text = (
            f"✅ Заявка №{order_id} принята!\n\n{card}\n\n"
            "📌 Что подготовить: освободить место у стены, оставить коробки и "
            "инструкцию рядом, проверить наличие фурнитуры.\n\nСпасибо за доверие! 🙌"
        )
    else:
        final_text = f"✅ Заявка №{order_id} принята! Мастер свяжется с вами в течение 15 минут. Спасибо! 🙌"

    await target.answer(final_text, reply_markup=booking_done_keyboard())
    await state.clear()


# --------------------------- ответы пользователя в квизе -------------

@router.message(OrderSteps.quiz, F.photo)
async def quiz_photo(message: Message, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    idx = data["step_index"]
    if idx >= len(steps) or steps[idx].kind != "photo":
        return
    answers = data.get("answers", {})
    answers["photo"] = message.photo[-1].file_id
    await state.update_data(answers=answers)
    await message.answer("Спасибо, получил! 📸")
    await _advance(message, state, db, masters_chat_id)


@router.message(OrderSteps.quiz, F.contact)
async def quiz_contact(message: Message, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    idx = data["step_index"]
    if idx >= len(steps) or steps[idx].kind != "phone":
        return
    answers = data.get("answers", {})
    answers["phone"] = message.contact.phone_number
    await state.update_data(answers=answers)
    await message.answer("Номер получен ✅", reply_markup=ReplyKeyboardRemove())
    await _advance(message, state, db, masters_chat_id)


@router.message(OrderSteps.quiz, F.text)
async def quiz_text(message: Message, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    data = await state.get_data()
    awaiting = data.get("awaiting")

    if awaiting == "custom_date":
        date_text = message.text.strip()
        if not (1 <= len(date_text) <= 30):
            await message.answer("Укажите дату короче, например: 24.07")
            return
        answers = data.get("answers", {})
        answers["order_date"] = date_text
        await state.update_data(answers=answers)
        await _ask_time(message, state)
        return

    if awaiting != "quiz_answer":
        return

    steps = get_steps(data["flow"])
    idx = data["step_index"]
    step = steps[idx]

    if step.kind == "text":
        text = message.text.strip()
        if not (1 <= len(text) <= 60):
            await message.answer("Введите текст покороче — до 60 символов.")
            return
        answers = data.get("answers", {})
        answers[step.key] = text
        await state.update_data(answers=answers)
        await _advance(message, state, db, masters_chat_id)
        return

    if step.kind == "phone":
        text = message.text.strip()
        if not PHONE_RE.search(text):
            await message.answer(
                "Введите номер в формате +7 999 123-45-67 или нажмите кнопку контакта.",
                reply_markup=contact_request_keyboard(),
            )
            return
        answers = data.get("answers", {})
        answers["phone"] = text
        await state.update_data(answers=answers)
        await message.answer("Номер получен ✅", reply_markup=ReplyKeyboardRemove())
        await _advance(message, state, db, masters_chat_id)
        return

    await message.answer("Пожалуйста, выберите вариант кнопкой выше 👆")


# --------------------------- inline-навигация квиза -------------------

@router.callback_query(OrderSteps.quiz, F.data.startswith("opt_"))
async def quiz_option_chosen(callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    step = steps[data["step_index"]]
    prefix = f"opt_{step.key}_"
    if not callback.data.startswith(prefix):
        await callback.answer()
        return

    code = callback.data[len(prefix):]
    answers = data.get("answers", {})
    answers[step.key] = code
    await state.update_data(answers=answers)
    await _advance(callback.message, state, db, masters_chat_id, edit=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data == "nav_skip")
async def nav_skip(callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    data = await state.get_data()
    steps = get_steps(data["flow"])
    step = steps[data["step_index"]]
    if step.required:
        await callback.answer("Этот шаг нельзя пропустить.", show_alert=True)
        return

    answers = data.get("answers", {})
    answers[step.key] = None
    await state.update_data(answers=answers)
    await _advance(callback.message, state, db, masters_chat_id, edit=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data == "nav_master")
async def nav_master(callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    await _submit_order(callback.message, state, db, masters_chat_id, urgent=True, to_manager=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data == "nav_back")
async def nav_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    screen = data.get("screen", "quiz")

    if screen == "quiz":
        idx = max(0, data["step_index"] - 1)
        await state.update_data(step_index=idx)
        await _ask_step(callback.message, state, edit=True)
    elif screen == "date":
        await _show_price_result(callback.message, state, edit=True)
    elif screen == "time":
        await _ask_date(callback.message, state, edit=True)

    await callback.answer()


# --------------------------- экран результата: цена -------------------

@router.callback_query(OrderSteps.quiz, F.data == "res_book")
async def res_book(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_date(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data == "res_call")
async def res_call(callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    await _submit_order(callback.message, state, db, masters_chat_id, urgent=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data == "res_edit")
async def res_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(step_index=0)
    await _ask_step(callback.message, state, edit=True)
    await callback.answer()


# --------------------------- запись на дату/время ----------------------

@router.callback_query(OrderSteps.quiz, F.data == "date_other")
async def date_other(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(awaiting="custom_date")
    await callback.message.edit_text("Напишите дату текстом (например: 24.07):")
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data.startswith("date_"))
async def date_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split("_", 1)[1]
    data = await state.get_data()
    label = dict(data.get("date_options", {})).get(code, code)
    answers = data.get("answers", {})
    answers["order_date"] = label
    await state.update_data(answers=answers)
    await _ask_time(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(OrderSteps.quiz, F.data.startswith("time_"))
async def time_chosen(callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int) -> None:
    slot = callback.data.split("_", 1)[1]
    data = await state.get_data()
    answers = data.get("answers", {})
    answers["time_slot"] = slot
    await state.update_data(answers=answers)
    await _submit_order(callback.message, state, db, masters_chat_id, scheduled=True)
    await callback.answer()


# --------------------------- глобальные кнопки (работают и после state.clear()) ---

@router.callback_query(F.data == "res_menu")
async def res_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Ок, вернул в главное меню 👇")
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "show_call")
async def show_call(callback: CallbackQuery) -> None:
    await callback.message.answer(f"📞 {CONTACT_PHONE}")
    await callback.answer()
