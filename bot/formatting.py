from typing import Optional

from bot.pricing import label_for


def _line(icon: str, value) -> str:
    return f"{icon} {value}" if value else ""


def format_order_card(
    order_id: Optional[int],
    name: str,
    phone: str,
    service: Optional[str],
    volume: Optional[str],
    demontage: Optional[str],
    hardware: Optional[str],
    district: Optional[str],
    timing: Optional[str],
    price_low: Optional[int],
    price_high: Optional[int],
    order_date: Optional[str],
    time_slot: Optional[str],
    urgent: bool = False,
) -> str:
    """Единая карточка заказа — используется и в подтверждении клиенту,
    и в сообщении для мастеров.

    order_id=None используется для превью цены до сохранения заявки в базу.
    """
    lines = []
    if urgent:
        lines.append("⚡ ПРИОРИТЕТ — клиент просит связаться быстрее")

    lines.append(f"📋 Заявка №{order_id}" if order_id is not None else "📋 Расчёт стоимости")
    lines.append(f"👤 {name or 'не указано'}")
    lines.append(f"📞 {phone or 'не указано'}")

    if service:
        lines.append(f"🪑 {label_for(service)}")
    if volume:
        lines.append(f"📐 Объём: {label_for(volume)}")
    if demontage:
        lines.append(f"🔨 Демонтаж: {label_for(demontage)}")
    if hardware:
        lines.append(f"🧩 Фурнитура: {label_for(hardware)}")
    if district:
        lines.append(f"📍 Район: {label_for(district)}")
    if timing:
        lines.append(f"⏱ Сроки: {label_for(timing)}")
    if price_low and price_high:
        lines.append(f"💰 Ориентир: {price_low:,}–{price_high:,} ₽".replace(",", " "))
    if order_date or time_slot:
        slot_labels = {"morning": "утро", "day": "день", "evening": "вечер"}
        slot = slot_labels.get(time_slot, time_slot or "")
        lines.append(f"📅 {order_date or 'дата уточняется'}  🕒 {slot or 'время уточняется'}")

    return "\n".join(lines)
