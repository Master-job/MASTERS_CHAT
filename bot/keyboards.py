from aiogram.utils.keyboard import InlineKeyboardBuilder

def services_keyboard():
    builder = InlineKeyboardBuilder()
    items = ["Шкаф", "Кровать", "Комод", "Гостиная", "Другое"]
    for i in items: builder.button(text=i, callback_data=f"svc_{i}")
    return builder.adjust(2).as_markup()

def amount_keyboard():
    builder = InlineKeyboardBuilder()
    for n in ["1", "2", "3+"]: builder.button(text=n, callback_data=f"amt_{n}")
    return builder.adjust(3).as_markup()

def condition_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="В коробках", callback_data="cond_new")
    builder.button(text="Частично", callback_data="cond_part")
    builder.button(text="Почти готово", callback_data="cond_done")
    return builder.adjust(1).as_markup()

def location_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Москва", callback_data="loc_msk")
    builder.button(text="МО", callback_data="loc_mo")
    return builder.as_markup()

def timing_keyboard():
    builder = InlineKeyboardBuilder()
    for t in ["Сегодня", "Завтра", "3 дня", "Неделя"]: builder.button(text=t, callback_data=f"time_{t}")
    return builder.adjust(2).as_markup()

def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Отправить мастеру", callback_data="order_send")
    return builder.as_markup()