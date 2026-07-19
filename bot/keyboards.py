from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Код -> подпись на кнопке. Не меняйте код у существующих пунктов задним
# числом — старые кнопки в чужих чатах должны продолжать работать.
SERVICES = {
    "wardrobe": "Шкаф 🗄",
    "bed": "Кровать 🛏",
    "chest": "Комод 🗃",
    "living_room": "Гостиная 🛋",
    "other": "Другое ✏️",
}


def services_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in SERVICES.items():
        builder.button(text=label, callback_data=f"svc_{code}")
    builder.adjust(2)
    return builder.as_markup()


def elevator_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Есть лифт", callback_data="lift_yes")
    builder.button(text="🚫 Нет лифта", callback_data="lift_no")
    builder.adjust(2)
    return builder.as_markup()


def skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Кнопка "Пропустить" для необязательных шагов квиза (фото, комментарий)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Пропустить", callback_data=callback_data)
    return builder.as_markup()


def confirm_order_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Всё верно, отправить", callback_data="order_send")
    builder.button(text="🔄 Начать заново", callback_data="order_restart")
    builder.adjust(1)
    return builder.as_markup()


def take_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛠 Взять в работу", callback_data=f"take_{order_id}")
    return builder.as_markup()


def master_outcome_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Показывается мастеру в личке после того, как он взял заказ и созвонился с клиентом."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Договорились, заказ подтверждён", callback_data=f"confirm_{order_id}")
    builder.button(text="❌ Не получилось, вернуть в пул", callback_data=f"release_{order_id}")
    builder.adjust(1)
    return builder.as_markup()
