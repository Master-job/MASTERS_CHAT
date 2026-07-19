"""Справочники квиза и калькулятор ориентировочной цены.

ВСЕ ЦИФРЫ НИЖЕ — ПРИМЕРНЫЕ. Отредактируйте под свои реальные расценки,
это единственное место, где нужно менять цены.
"""

# (код, подпись на кнопке)
SERVICE_OPTIONS = [
    ("wardrobe", "🚪 Шкаф-купе / гардероб"),
    ("bed_chest", "🛏 Кровать / комод"),
    ("wall_unit", "🗄 Модульная стенка / гарнитур"),
    ("kids_hall", "🪑 Детская / прихожая"),
    ("office", "💼 Офисная мебель"),
    ("multiple", "📦 Несколько предметов"),
]

VOLUME_OPTIONS = [
    ("one_item", "1 предмет"),
    ("one_room", "Комната целиком"),
    ("apartment", "Несколько комнат / квартира"),
]

DEMONTAGE_OPTIONS = [
    ("yes", "Да, демонтировать"),
    ("no", "Нет, только сборка"),
    ("partial", "Частично"),
]

HARDWARE_OPTIONS = [
    ("ok", "Всё есть ✅"),
    ("no_instructions", "Нет инструкции"),
    ("missing_parts", "Утеряны/не хватает деталей"),
    ("unknown", "Не знаю"),
]

DISTRICT_OPTIONS = [
    ("cao", "ЦАО"), ("sao", "САО"),
    ("svao", "СВАО"), ("vao", "ВАО"),
    ("yuvao", "ЮВАО"), ("yuao", "ЮАО"),
    ("yuzao", "ЮЗАО"), ("zao", "ЗАО"),
    ("szao", "СЗАО"), ("zelao", "Зеленоград"),
    ("new_moscow", "Новая Москва"),
    ("other", "Другой район / за городом"),
]

TIMING_OPTIONS = [
    ("urgent", "🔥 Срочно (сегодня/завтра)"),
    ("soon", "📅 В ближайшие дни"),
    ("flexible", "🗓 Дата гибкая"),
    ("looking", "❓ Пока присматриваюсь"),
]

# label-словари для карточек и текстов
_LABELS = {
    code: label
    for group in (SERVICE_OPTIONS, VOLUME_OPTIONS, DEMONTAGE_OPTIONS,
                   HARDWARE_OPTIONS, DISTRICT_OPTIONS, TIMING_OPTIONS)
    for code, label in group
}


def label_for(code: str) -> str:
    return _LABELS.get(code, code or "не указано")


# --- калькулятор цены -------------------------------------------------
# (нижняя граница, верхняя граница) за базовую единицу услуги
_SERVICE_BASE = {
    "wardrobe": (2500, 5500),
    "bed_chest": (1500, 3500),
    "wall_unit": (3500, 9000),
    "kids_hall": (1800, 4500),
    "office": (2000, 6000),
    "multiple": (4000, 12000),
}

_VOLUME_MULT = {
    "one_item": 1.0,
    "one_room": 1.6,
    "apartment": 2.4,
    None: 1.0,
}

_DEMONTAGE_ADD = {"yes": 800, "partial": 400, "no": 0, None: 0}
_HARDWARE_ADD = {
    "no_instructions": 500,
    "missing_parts": 1200,
    "unknown": 300,
    "ok": 0,
    None: 0,
}


def calculate_price(answers: dict) -> tuple[int, int]:
    """Возвращает (низ, верх) диапазона цены в рублях, округлённые до сотен."""
    base_low, base_high = _SERVICE_BASE.get(answers.get("service"), (2000, 6000))
    mult = _VOLUME_MULT.get(answers.get("volume"), 1.0)
    add = _DEMONTAGE_ADD.get(answers.get("demontage"), 0) + _HARDWARE_ADD.get(
        answers.get("hardware"), 0
    )

    low = round((base_low * mult + add) / 100) * 100
    high = round((base_high * mult + add) / 100) * 100
    return int(low), int(high)


# --- статические тексты для кнопок главного меню -----------------------

CONTACT_PHONE = "+7 900 000-00-00"  # ЗАМЕНИТЕ на свой номер

FAQ_TEXT = (
    "❓ Частые вопросы\n\n"
    "• Выезд по Москве в пределах МКАД включён в стоимость сборки.\n"
    "• Гарантию на работу даёт мастер, который её выполнял.\n"
    "• Кухни и встроенную технику не собираем — только корпусная мебель.\n"
    "• Точная цена называется мастером после фото/осмотра.\n\n"
    f"Можно просто позвонить: {CONTACT_PHONE}"
)

EXAMPLES_TEXT = (
    "📸 Примеры работ\n\n"
    "Здесь пока заглушка — пришлите нам реальные фото собранной мебели, "
    "и мы вставим их в этот раздел (или разработчик добавит send_photo "
    "с вашими file_id прямо в код)."
)

REVIEWS_TEXT = (
    "⭐ Отзывы\n\n"
    "Здесь пока заглушка — добавьте реальные отзывы клиентов, когда они появятся."
)
