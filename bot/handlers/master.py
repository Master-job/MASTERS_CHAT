import logging
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database import Database
from bot.formatting import format_order_card
from bot.keyboards import master_outcome_keyboard, take_order_keyboard

logger = logging.getLogger(__name__)
router = Router(name="master")


def _order_card(order) -> str:
    return format_order_card(
        order_id=order.id,
        name=order.name,
        phone=order.phone,
        address=order.address,
        floor=order.floor,
        has_elevator=order.has_elevator,
        service_code=order.service,
        details=order.details,
        order_date=order.order_date,
        order_time=order.order_time,
        comment=order.comment,
    )


def _parse_order_id(callback_data: str) -> Optional[int]:
    try:
        return int(callback_data.split("_", 1)[1])
    except (IndexError, ValueError):
        return None


# ------------------------------------------------------------- взять заказ

@router.callback_query(F.data.startswith("take_"))
async def master_take(callback: CallbackQuery, db: Database) -> None:
    order_id = _parse_order_id(callback.data)
    if order_id is None:
        await callback.answer("Некорректный заказ.", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    master = callback.from_user
    master_label = master.username or master.full_name

    won = await db.take_order(order_id, master.id, master_label)
    if not won:
        await callback.answer("🛑 Этот заказ уже забрал другой мастер!", show_alert=True)
        return

    # Обновляем карточку в чате мастеров: убираем кнопку, показываем кто взял.
    new_caption = f"{_order_card(order)}\n\n🕐 В РАБОТЕ: @{master_label}"
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=new_caption)
        else:
            await callback.message.edit_text(text=new_caption)
    except Exception:
        logger.warning("Не удалось обновить карточку заказа №%s в группе", order_id)

    # Мастеру в личку — полная карточка + кнопки "договорились / не вышло".
    try:
        card = _order_card(order)
        if order.photo_file_id:
            await callback.bot.send_photo(
                master.id, order.photo_file_id, caption=card,
                reply_markup=master_outcome_keyboard(order_id),
            )
        else:
            await callback.bot.send_message(
                master.id, card, reply_markup=master_outcome_keyboard(order_id)
            )
    except Exception:
        # Мастер ни разу не писал боту в личку -> Telegram не даёт написать первым.
        logger.warning("Не удалось написать мастеру %s в личные сообщения", master.id)
        await callback.answer(
            "Заказ ваш! Но сначала напишите боту /start в личных сообщениях, "
            "чтобы получать карточки заказов и подтверждать их.",
            show_alert=True,
        )
        return

    await callback.answer("Заказ закреплён за вами, детали — в личных сообщениях от бота.")


# ------------------------------------------------------- итог по заказу ---

@router.callback_query(F.data.startswith("confirm_"))
async def master_confirm(callback: CallbackQuery, db: Database) -> None:
    order_id = _parse_order_id(callback.data)
    if order_id is None:
        await callback.answer("Некорректный заказ.", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    ok = await db.confirm_order(order_id, callback.from_user.id)
    if not ok:
        await callback.answer("Этот заказ уже не в статусе «в работе» у вас.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Заказ №{order_id} подтверждён. Удачной сборки!")

    try:
        await callback.bot.send_message(
            order.client_chat_id,
            f"✅ Мастер подтвердил заявку №{order_id} и свяжется с вами по "
            f"{order.order_date} в {order.order_time}.",
        )
    except Exception:
        logger.warning("Не удалось уведомить клиента по заказу №%s", order_id)

    await callback.answer()


@router.callback_query(F.data.startswith("release_"))
async def master_release(callback: CallbackQuery, db: Database, masters_chat_id: int) -> None:
    order_id = _parse_order_id(callback.data)
    if order_id is None:
        await callback.answer("Некорректный заказ.", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден.", show_alert=True)
        return

    ok = await db.release_order(order_id, callback.from_user.id)
    if not ok:
        await callback.answer("Этот заказ уже не в статусе «в работе» у вас.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"🔄 Заказ №{order_id} возвращён в общий пул.")

    # Возвращаем карточку в чате мастеров с активной кнопкой "Взять в работу".
    if order.group_chat_id and order.group_message_id:
        try:
            new_caption = f"{_order_card(order)}\n\n🔄 Снова свободен"
            if order.photo_file_id:
                await callback.bot.edit_message_caption(
                    chat_id=order.group_chat_id,
                    message_id=order.group_message_id,
                    caption=new_caption,
                    reply_markup=take_order_keyboard(order_id),
                )
            else:
                await callback.bot.edit_message_text(
                    chat_id=order.group_chat_id,
                    message_id=order.group_message_id,
                    text=new_caption,
                    reply_markup=take_order_keyboard(order_id),
                )
        except Exception:
            logger.warning("Не удалось вернуть карточку заказа №%s в группу", order_id)
            # На случай, если редактирование не удалось — публикуем новое сообщение,
            # чтобы заказ точно не потерялся.
            try:
                sent = await callback.bot.send_message(
                    masters_chat_id,
                    f"{_order_card(order)}\n\n🔄 Снова свободен",
                    reply_markup=take_order_keyboard(order_id),
                )
                await db.set_group_message(order_id, sent.chat.id, sent.message_id)
            except Exception:
                logger.exception("Не удалось republish заказ №%s в группу", order_id)

    await callback.answer()
