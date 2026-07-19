import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.database import Database
from bot.formatting import format_order_card
from bot.keyboards import (
    confirm_order_keyboard,
    elevator_keyboard,
    services_keyboard,
    skip_keyboard,
    take_order_keyboard,
)
from bot.states import OrderSteps

logger = logging.getLogger(__name__)
router = Router(name="client")

PHONE_RE = re.compile(r"[\d+][\d\s\-()]{8,17}\d")


def _contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ---------------------------------------------------------------- старт ----

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! 👋 Оформим заявку на сборку мебели — это займёт пару минут.\n\n"
        "Как к вам обращаться? (имя)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(OrderSteps.entering_name)


# --------------------------------------------------------------- имя -------

@router.message(OrderSteps.entering_name)
async def name_entered(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not (2 <= len(name) <= 60):
        await message.answer("Введите имя текстом, от 2 до 60 символов 🙂")
        return

    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}!\nПришлите номер телефона для связи:",
        reply_markup=_contact_keyboard(),
    )
    await state.set_state(OrderSteps.entering_phone)


# -------------------------------------------------------------- телефон ----

@router.message(OrderSteps.entering_phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await _ask_address(message, state)


@router.message(OrderSteps.entering_phone, F.text)
async def phone_from_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not PHONE_RE.search(text):
        await message.answer(
            "Не похоже на номер телефона. Введите в формате +7 999 123-45-67 "
            "или нажмите кнопку ниже.",
            reply_markup=_contact_keyboard(),
        )
        return

    await state.update_data(phone=text)
    await _ask_address(message, state)


@router.message(OrderSteps.entering_phone)
async def phone_wrong_type(message: Message) -> None:
    await message.answer(
        "Пришлите номер телефона текстом или кнопкой ниже 👇",
        reply_markup=_contact_keyboard(),
    )


async def _ask_address(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Укажите адрес (город, улица, дом, квартира):",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(OrderSteps.entering_address)


# ---------------------------------------------------------------- адрес ----

@router.message(OrderSteps.entering_address)
async def address_entered(message: Message, state: FSMContext) -> None:
    address = (message.text or "").strip()
    if not (5 <= len(address) <= 200):
        await message.answer("Укажите адрес текстом, от 5 до 200 символов.")
        return

    await state.update_data(address=address)
    await message.answer("На каком этаже? (напишите число, например 8)")
    await state.set_state(OrderSteps.entering_floor)


# ---------------------------------------------------------------- этаж -----

@router.message(OrderSteps.entering_floor)
async def floor_entered(message: Message, state: FSMContext) -> None:
    floor = (message.text or "").strip()
    if not (1 <= len(floor) <= 10):
        await message.answer("Укажите этаж коротко, например: 8")
        return

    await state.update_data(floor=floor)
    await message.answer("Есть лифт в доме?", reply_markup=elevator_keyboard())
    await state.set_state(OrderSteps.choosing_elevator)


@router.callback_query(OrderSteps.choosing_elevator, F.data.in_({"lift_yes", "lift_no"}))
async def elevator_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    has_elevator = callback.data == "lift_yes"
    await state.update_data(has_elevator=has_elevator)
    await callback.message.edit_text(
        f"Лифт: {'есть ✔️' if has_elevator else 'нет 🚫'}"
    )
    await callback.message.answer("Что нужно собрать?", reply_markup=services_keyboard())
    await state.set_state(OrderSteps.choosing_service)
    await callback.answer()


# -------------------------------------------------------------- услуга ----

@router.callback_query(OrderSteps.choosing_service, F.data.startswith("svc_"))
async def service_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split("_", 1)[1]
    from bot.keyboards import SERVICES  # локальный импорт, чтобы не плодить циклы

    label = SERVICES.get(code)
    if not label:
        await callback.answer("Неизвестная услуга, попробуйте ещё раз.", show_alert=True)
        return

    await state.update_data(service=code)
    await callback.message.edit_text(f"Вы выбрали: {label}")
    await callback.message.answer(
        "Опишите мебель подробнее (бренд/модель, сколько дверей/секций и т.п.):"
    )
    await state.set_state(OrderSteps.entering_details)
    await callback.answer()


@router.callback_query(OrderSteps.choosing_service)
async def service_wrong_input(callback: CallbackQuery) -> None:
    await callback.answer("Пожалуйста, выберите вариант кнопкой ниже 👇", show_alert=True)


# --------------------------------------------------------------- детали ---

@router.message(OrderSteps.entering_details)
async def details_entered(message: Message, state: FSMContext) -> None:
    details = (message.text or "").strip()
    if not (2 <= len(details) <= 300):
        await message.answer("Опишите мебель текстом, от 2 до 300 символов.")
        return

    await state.update_data(details=details)
    await message.answer(
        "Пришлите фото мебели или чертёж — так мастеру проще оценить работу.\n"
        "Либо нажмите «Пропустить».",
        reply_markup=skip_keyboard("skip_photo"),
    )
    await state.set_state(OrderSteps.uploading_photo)


# ---------------------------------------------------------------- фото ----

@router.message(OrderSteps.uploading_photo, F.photo)
async def photo_uploaded(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await message.answer("Фото получено ✅")
    await _ask_date(message, state)


@router.callback_query(OrderSteps.uploading_photo, F.data == "skip_photo")
async def photo_skipped(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(photo_file_id=None)
    await callback.message.edit_text("Фото пропущено.")
    await _ask_date(callback.message, state)
    await callback.answer()


@router.message(OrderSteps.uploading_photo)
async def photo_wrong_type(message: Message) -> None:
    await message.answer(
        "Пришлите фото мебели или нажмите «Пропустить» кнопкой выше.",
        reply_markup=skip_keyboard("skip_photo"),
    )


async def _ask_date(message: Message, state: FSMContext) -> None:
    await message.answer("На какую дату нужна сборка? (например: 24.07 или «завтра»)")
    await state.set_state(OrderSteps.entering_date)


# ----------------------------------------------------------- дата/время --

@router.message(OrderSteps.entering_date)
async def date_entered(message: Message, state: FSMContext) -> None:
    date_text = (message.text or "").strip()
    if not (1 <= len(date_text) <= 30):
        await message.answer("Укажите дату короче, например: 24.07")
        return

    await state.update_data(order_date=date_text)
    await message.answer("На какое время? (например: 14:00 или «после 18:00»)")
    await state.set_state(OrderSteps.entering_time)


@router.message(OrderSteps.entering_time)
async def time_entered(message: Message, state: FSMContext) -> None:
    time_text = (message.text or "").strip()
    if not (1 <= len(time_text) <= 30):
        await message.answer("Укажите время короче, например: 14:00")
        return

    await state.update_data(order_time=time_text)
    await message.answer(
        "Есть что-то важное для мастера? (закрепить к стене, позвонить заранее и т.п.)\n"
        "Если нет — нажмите «Пропустить».",
        reply_markup=skip_keyboard("skip_comment"),
    )
    await state.set_state(OrderSteps.entering_comment)


# -------------------------------------------------------------- комментарий

@router.message(OrderSteps.entering_comment)
async def comment_entered(message: Message, state: FSMContext) -> None:
    comment = (message.text or "").strip()
    if len(comment) > 300:
        await message.answer("Покороче, пожалуйста — до 300 символов.")
        return

    await state.update_data(comment=comment or None)
    await _show_summary(message, state)


@router.callback_query(OrderSteps.entering_comment, F.data == "skip_comment")
async def comment_skipped(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(comment=None)
    await callback.message.edit_text("Без комментария.")
    await _show_summary(callback.message, state)
    await callback.answer()


async def _show_summary(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    card = format_order_card(
        order_id=None,
        name=data["name"],
        phone=data["phone"],
        address=data["address"],
        floor=data["floor"],
        has_elevator=data["has_elevator"],
        service_code=data["service"],
        details=data["details"],
        order_date=data["order_date"],
        order_time=data["order_time"],
        comment=data.get("comment"),
    )

    await message.answer(
        f"Проверьте, всё верно?\n\n{card}",
        reply_markup=confirm_order_keyboard(),
    )
    await state.set_state(OrderSteps.confirming)


# ------------------------------------------------------------ подтверждение

@router.callback_query(OrderSteps.confirming, F.data == "order_restart")
async def order_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Хорошо, начнём заново.")
    await callback.message.answer("Как к вам обращаться? (имя)")
    await state.set_state(OrderSteps.entering_name)
    await callback.answer()


@router.callback_query(OrderSteps.confirming, F.data == "order_send")
async def order_send(
    callback: CallbackQuery, state: FSMContext, db: Database, masters_chat_id: int
) -> None:
    data = await state.get_data()

    order_id = await db.create_order(
        client_chat_id=callback.message.chat.id,
        name=data["name"],
        phone=data["phone"],
        address=data["address"],
        floor=data["floor"],
        has_elevator=data["has_elevator"],
        service=data["service"],
        details=data["details"],
        photo_file_id=data.get("photo_file_id"),
        order_date=data["order_date"],
        order_time=data["order_time"],
        comment=data.get("comment"),
    )

    card = format_order_card(
        order_id=order_id,
        name=data["name"],
        phone=data["phone"],
        address=data["address"],
        floor=data["floor"],
        has_elevator=data["has_elevator"],
        service_code=data["service"],
        details=data["details"],
        order_date=data["order_date"],
        order_time=data["order_time"],
        comment=data.get("comment"),
    )

    try:
        photo_id = data.get("photo_file_id")
        if photo_id:
            sent = await callback.bot.send_photo(
                masters_chat_id, photo_id, caption=card, reply_markup=take_order_keyboard(order_id)
            )
        else:
            sent = await callback.bot.send_message(
                masters_chat_id, card, reply_markup=take_order_keyboard(order_id)
            )
        await db.set_group_message(order_id, sent.chat.id, sent.message_id)
    except Exception:
        logger.exception("Не удалось отправить заявку №%s в чат мастеров", order_id)
        await callback.message.edit_text(
            "⚠️ Заявка сохранена, но не удалось передать её мастерам. "
            "Мы разберёмся и свяжемся с вами."
        )
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(
        f"✅ Заявка №{order_id} передана мастерам! Как только кто-то возьмёт "
        f"её в работу — вам напишут и позвонят по указанному номеру."
    )
    await state.clear()
    await callback.answer()
