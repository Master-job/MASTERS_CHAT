from typing import Optional

from bot.keyboards import SERVICES


def service_label(code: str) -> str:
    return SERVICES.get(code, code)


def format_order_card(
    order_id: Optional[int],
    name: str,
    phone: str,
    address: str,
    floor: str,
    has_elevator: bool,
    service_code: str,
    details: str,
    order_date: str,
    order_time: str,
    comment: Optional[str],
) -> str:
    """Единый формат карточки заказа — используется и в подтверждении клиенту,
    и в сообщении для мастеров, чтобы они не отличались.

    order_id=None используется для превью до сохранения заявки в базу
    (шаг "проверьте, всё верно?").
    """
    lift = "✔️ есть" if has_elevator else "🚫 нет, только по лестнице"
    lines = [
        f"📋 Заявка №{order_id}" if order_id is not None else "📋 Новая заявка",
        f"👤 {name}",
        f"📞 {phone}",
        f"📍 {address}",
        f"🏢 Этаж: {floor} | Лифт: {lift}",
        f"🪑 {service_label(service_code)}: {details}",
        f"📅 {order_date}   🕒 {order_time}",
    ]
    if comment:
        lines.append(f"📝 {comment}")
    return "\n".join(lines)
