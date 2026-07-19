def format_order_card(data):
    return (
        f"📋 <b>Новая заявка</b>\n"
        f"👤 Клиент: {data.get('name')}\n"
        f"📞 {data.get('phone')}\n"
        f"🛠 Мебель: {data.get('service')}\n"
        f"🔢 Кол-во: {data.get('amount')}\n"
        f"📦 Состояние: {data.get('condition')}\n"
        f"📍 Локация: {data.get('location')} ({data.get('district', '-')})\n"
        f"📅 Срок: {data.get('timing')}\n"
        f"🖼 Фото: {'✅ есть' if data.get('photo') else 'нет'}"
    )