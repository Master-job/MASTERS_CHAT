import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# new -> taken -> confirmed (финал) | taken -> new (мастер не смог договориться)


@dataclass
class Order:
    id: int
    client_chat_id: int
    name: str
    phone: str
    service: Optional[str]
    volume: Optional[str]
    demontage: Optional[str]
    hardware: Optional[str]
    district: Optional[str]
    timing: Optional[str]
    photo_file_id: Optional[str]
    price_low: Optional[int]
    price_high: Optional[int]
    order_date: Optional[str]
    time_slot: Optional[str]
    urgent: bool
    status: str
    taken_by_id: Optional[int]
    taken_by_username: Optional[str]
    group_chat_id: Optional[int]
    group_message_id: Optional[int]
    created_at: str


class Database:
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
                name TEXT,
                phone TEXT,
                service TEXT,
                volume TEXT,
                demontage TEXT,
                hardware TEXT,
                district TEXT,
                timing TEXT,
                photo_file_id TEXT,
                price_low INTEGER,
                price_high INTEGER,
                order_date TEXT,
                time_slot TEXT,
                urgent INTEGER NOT NULL DEFAULT 0,
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
            id=row["id"], client_chat_id=row["client_chat_id"],
            name=row["name"], phone=row["phone"],
            service=row["service"], volume=row["volume"],
            demontage=row["demontage"], hardware=row["hardware"],
            district=row["district"], timing=row["timing"],
            photo_file_id=row["photo_file_id"],
            price_low=row["price_low"], price_high=row["price_high"],
            order_date=row["order_date"], time_slot=row["time_slot"],
            urgent=bool(row["urgent"]), status=row["status"],
            taken_by_id=row["taken_by_id"], taken_by_username=row["taken_by_username"],
            group_chat_id=row["group_chat_id"], group_message_id=row["group_message_id"],
            created_at=row["created_at"],
        )

    async def create_order(self, client_chat_id: int, urgent: bool = False, **fields) -> int:
        columns = [
            "service", "volume", "demontage", "hardware", "district", "timing",
            "photo_file_id", "name", "phone", "price_low", "price_high",
            "order_date", "time_slot",
        ]
        values = [fields.get(col) for col in columns]

        cursor = await self._conn.execute(
            f"""
            INSERT INTO orders (client_chat_id, urgent, status, created_at, {", ".join(columns)})
            VALUES (?, ?, 'new', ?, {", ".join("?" for _ in columns)})
            """,
            [client_chat_id, int(urgent), datetime.now(timezone.utc).isoformat(), *values],
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
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'taken', taken_by_id = ?, taken_by_username = ? "
            "WHERE id = ? AND status = 'new'",
            (master_id, master_username, order_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def confirm_order(self, order_id: int, master_id: int) -> bool:
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'confirmed' WHERE id = ? AND status = 'taken' "
            "AND taken_by_id = ?",
            (order_id, master_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def release_order(self, order_id: int, master_id: int) -> bool:
        cursor = await self._conn.execute(
            "UPDATE orders SET status = 'new', taken_by_id = NULL, taken_by_username = NULL "
            "WHERE id = ? AND status = 'taken' AND taken_by_id = ?",
            (order_id, master_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0
