import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Жизненный цикл заявки:
# new       -> заявка опубликована в чате мастеров, свободна
# taken     -> мастер нажал "Взять в работу", звонит клиенту, обсуждает детали
# confirmed -> мастер подтвердил, что договорился с клиентом (финал, заказ состоялся)
# new (again) -> если мастер не смог договориться, заявка возвращается в пул


@dataclass
class Order:
    id: int
    client_chat_id: int
    name: str
    phone: str
    address: str
    floor: str
    has_elevator: bool
    service: str
    details: str
    photo_file_id: Optional[str]
    order_date: str
    order_time: str
    comment: Optional[str]
    status: str
    taken_by_id: Optional[int]
    taken_by_username: Optional[str]
    group_chat_id: Optional[int]
    group_message_id: Optional[int]
    created_at: str


class Database:
    """Асинхронная обёртка над SQLite — хранит заявки и их статус."""

    def __init__(self, path: str = "orders.db"):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                floor TEXT NOT NULL,
                has_elevator INTEGER NOT NULL,
                service TEXT NOT NULL,
                details TEXT NOT NULL,
                photo_file_id TEXT,
                order_date TEXT NOT NULL,
                order_time TEXT NOT NULL,
                comment TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                taken_by_id INTEGER,
                taken_by_username TEXT,
                group_chat_id INTEGER,
                group_message_id INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._conn.commit()
        logger.info("База данных подключена: %s", self.path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    @staticmethod
    def _row_to_order(row: aiosqlite.Row) -> Order:
        return Order(
            id=row["id"],
            client_chat_id=row["client_chat_id"],
            name=row["name"],
            phone=row["phone"],
            address=row["address"],
            floor=row["floor"],
            has_elevator=bool(row["has_elevator"]),
            service=row["service"],
            details=row["details"],
            photo_file_id=row["photo_file_id"],
            order_date=row["order_date"],
            order_time=row["order_time"],
            comment=row["comment"],
            status=row["status"],
            taken_by_id=row["taken_by_id"],
            taken_by_username=row["taken_by_username"],
            group_chat_id=row["group_chat_id"],
            group_message_id=row["group_message_id"],
            created_at=row["created_at"],
        )

    async def create_order(
        self,
        client_chat_id: int,
        name: str,
        phone: str,
        address: str,
        floor: str,
        has_elevator: bool,
        service: str,
        details: str,
        photo_file_id: Optional[str],
        order_date: str,
        order_time: str,
        comment: Optional[str],
    ) -> int:
        cursor = await self._conn.execute(
            """
            INSERT INTO orders (
                client_chat_id, name, phone, address, floor, has_elevator,
                service, details, photo_file_id, order_date, order_time,
                comment, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """,
            (
                client_chat_id, name, phone, address, floor, int(has_elevator),
                service, details, photo_file_id, order_date, order_time,
                comment, datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def set_group_message(self, order_id: int, chat_id: int, message_id: int) -> None:
        await self._conn.execute(
            "UPDATE orders SET group_chat_id = ?, group_message_id = ? WHERE id = ?",
            (chat_id, message_id, order_id),
        )
        await self._conn.commit()

    async def get_order(self, order_id: int) -> Optional[Order]:
        cursor = await self._conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return self._row_to_order(row) if row else None

    async def take_order(self, order_id: int, master_id: int, master_username: str) -> bool:
        """Атомарно переводит заявку new -> taken. True, если именно этот вызов победил."""
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'taken', taken_by_id = ?, taken_by_username = ? "
            "WHERE id = ? AND status = 'new'",
            (master_id, master_username, order_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def confirm_order(self, order_id: int, master_id: int) -> bool:
        """Мастер подтвердил, что договорился с клиентом. Финальный статус."""
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'confirmed' WHERE id = ? AND status = 'taken' "
            "AND taken_by_id = ?",
            (order_id, master_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def release_order(self, order_id: int, master_id: int) -> bool:
        """Мастер не смог договориться — заявка возвращается в пул для остальных."""
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'new', taken_by_id = NULL, taken_by_username = NULL "
            "WHERE id = ? AND status = 'taken' AND taken_by_id = ?",
            (order_id, master_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0
