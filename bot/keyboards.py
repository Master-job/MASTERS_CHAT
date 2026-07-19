from typing import List, Optional, Tuple

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.quiz_steps import Step

MENU_CALC = "🧮 Рассчитать стоимость"
MENU_FAST = "🛠 Заказать сборщика"
MENU_EXAMPLES = "📸 Примеры работ"
MENU_REVIEWS = "⭐ Отзывы"
MENU_FAQ = "❓ Вопросы и цены"
MENU_CALL = "📞 Позвонить"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_CALC), KeyboardButton(text=MENU_FAST)],
            [KeyboardButton(text=MENU_EXAMPLES), KeyboardButton(text=MENU_REVIEWS)],
            [KeyboardButton(text=MENU_FAQ), KeyboardButton(text=MENU_CALL)],
        ],
        resize_keyboard=True,
    )


def contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def quiz_keyboard(step: Step, step_index: int) -> Optional[InlineKeyboardMarkup]:
    """Клавиатура шага квиза: варианты ответа (если есть) + Назад/Пропустить/К мастеру."""
    builder = InlineKeyboardBuilder()

    if step.options:
        for code, label in step.options:
            builder.button(text=label, callback_data=f"opt_{step.key}_{code}")
        builder.adjust(step.columns)

    nav_buttons = []
    if step_index > 0:
        nav_buttons.append(_ib("🔙 Назад", "nav_back"))
    if not step.required:
        nav_buttons.append(_ib("⏭ Пропустить", "nav_skip"))
    nav_buttons.append(_ib("💬 К мастеру", "nav_master"))
    builder.row(*nav_buttons)

    return builder.as_markup()


def _ib(text: str, callback_data: str):
    from aiogram.types import InlineKeyboardButton
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def price_result_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться на время", callback_data="res_book")
    builder.button(text="☎️ Хочу звонок мастера", callback_data="res_call")
    builder.button(text="💬 Написать менеджеру", callback_data="nav_master")
    builder.button(text="🔙 Изменить ответы", callback_data="res_edit")
    builder.button(text="🏠 В меню", callback_data="res_menu")
    builder.adjust(1)
    return builder.as_markup()


def date_keyboard(dates: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in dates:
        builder.button(text=label, callback_data=f"date_{code}")
    builder.adjust(2)
    builder.row(_ib("✏️ Другая дата", "date_other"))
    builder.row(_ib("🔙 Назад", "nav_back"))
    return builder.as_markup()


def time_slot_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 Утро (9:00–12:00)", callback_data="time_morning")
    builder.button(text="☀️ День (12:00–16:00)", callback_data="time_day")
    builder.button(text="🌆 Вечер (16:00–20:00)", callback_data="time_evening")
    builder.adjust(1)
    builder.row(_ib("🔙 Назад", "nav_back"))
    return builder.as_markup()


def booking_done_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Позвонить", callback_data="show_call")
    builder.button(text="🏠 В меню", callback_data="res_menu")
    builder.adjust(1)
    return builder.as_markup()


def take_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛠 Взять в работу", callback_data=f"take_{order_id}")
    return builder.as_markup()


def master_outcome_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Договорились, заказ подтверждён", callback_data=f"confirm_{order_id}")
    builder.button(text="❌ Не получилось, вернуть в пул", callback_data=f"release_{order_id}")
    builder.adjust(1)
    return builder.as_markup()
