import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import aiosqlite
from app.database.models import Category, Service, Master, Client, Booking

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    @asynccontextmanager
    async def connect(self):
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_tables(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with self.connect() as conn:
            await conn.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT NOT NULL DEFAULT '✨'
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                price REAL NOT NULL,
                description TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT NOT NULL DEFAULT 'Мастер',
                phone TEXT DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                service_id INTEGER NOT NULL REFERENCES services(id),
                master_id INTEGER NOT NULL REFERENCES masters(id),
                booking_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_bookings_date_master ON bookings(booking_date, master_id, status);
            CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(client_id, status);
            """)
            await conn.commit()
            logger.info("Database tables initialized successfully.")

    # --- Categories ---
    async def get_categories(self) -> List[Category]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM categories ORDER BY id ASC") as cur:
                rows = await cur.fetchall()
                return [Category(**dict(row)) for row in rows]

    async def get_category(self, category_id: int) -> Optional[Category]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)) as cur:
                row = await cur.fetchone()
                return Category(**dict(row)) if row else None

    # --- Services ---
    async def get_services_by_category(self, category_id: int) -> List[Service]:
        async with self.connect() as conn:
            async with conn.execute(
                "SELECT * FROM services WHERE category_id = ? AND is_active = 1 ORDER BY name ASC",
                (category_id,)
            ) as cur:
                rows = await cur.fetchall()
                return [Service(**dict(row)) for row in rows]

    async def get_service(self, service_id: int) -> Optional[Service]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)) as cur:
                row = await cur.fetchone()
                return Service(**dict(row)) if row else None

    async def add_service(self, category_id: int, name: str, duration: int, price: float, description: str = "") -> int:
        async with self.connect() as conn:
            cur = await conn.execute(
                "INSERT INTO services (category_id, name, duration_minutes, price, description) VALUES (?, ?, ?, ?, ?)",
                (category_id, name, duration, price, description)
            )
            await conn.commit()
            return cur.lastrowid

    # --- Masters ---
    async def get_active_masters(self) -> List[Master]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM masters WHERE is_active = 1 ORDER BY id ASC") as cur:
                rows = await cur.fetchall()
                return [Master(**dict(row)) for row in rows]

    async def get_master(self, master_id: int) -> Optional[Master]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM masters WHERE id = ?", (master_id,)) as cur:
                row = await cur.fetchone()
                return Master(**dict(row)) if row else None

    # --- Clients ---
    async def get_or_create_client(self, telegram_id: int, full_name: str, phone: str) -> Client:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    if full_name or phone:
                        await conn.execute(
                            "UPDATE clients SET full_name = COALESCE(NULLIF(?, ''), full_name), phone = COALESCE(NULLIF(?, ''), phone) WHERE telegram_id = ?",
                            (full_name, phone, telegram_id)
                        )
                        await conn.commit()
                    async with conn.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)) as cur2:
                        updated_row = await cur2.fetchone()
                        return Client(**dict(updated_row))

            cur = await conn.execute(
                "INSERT INTO clients (telegram_id, full_name, phone) VALUES (?, ?, ?)",
                (telegram_id, full_name, phone)
            )
            await conn.commit()
            return Client(id=cur.lastrowid, telegram_id=telegram_id, full_name=full_name, phone=phone)

    async def get_client_by_telegram_id(self, telegram_id: int) -> Optional[Client]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)) as cur:
                row = await cur.fetchone()
                return Client(**dict(row)) if row else None

    async def get_all_clients(self) -> List[Client]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM clients ORDER BY id DESC") as cur:
                rows = await cur.fetchall()
                return [Client(**dict(row)) for row in rows]

    # --- Bookings & Scheduling ---
    async def check_collision(self, master_id: int, booking_date: str, start_time: str, end_time: str) -> bool:
        """Returns True if there is a conflict/collision, False if free."""
        async with self.connect() as conn:
            query = """
            SELECT COUNT(*) AS cnt FROM bookings
            WHERE master_id = ?
              AND booking_date = ?
              AND status = 'CONFIRMED'
              AND (
                  (start_time <= ? AND end_time > ?) OR
                  (start_time < ? AND end_time >= ?) OR
                  (start_time >= ? AND end_time <= ?)
              )
            """
            async with conn.execute(query, (master_id, booking_date, start_time, start_time, end_time, end_time, start_time, end_time)) as cur:
                row = await cur.fetchone()
                return row["cnt"] > 0

    async def create_booking(
        self,
        client_id: int,
        service_id: int,
        master_id: int,
        booking_date: str,
        start_time: str,
        end_time: str,
        notes: str = ""
    ) -> Optional[int]:
        """Creates a booking atomically if no collision exists."""
        async with self.connect() as conn:
            # Check collision under transaction
            query = """
            SELECT COUNT(*) AS cnt FROM bookings
            WHERE master_id = ?
              AND booking_date = ?
              AND status = 'CONFIRMED'
              AND (
                  (start_time <= ? AND end_time > ?) OR
                  (start_time < ? AND end_time >= ?) OR
                  (start_time >= ? AND end_time <= ?)
              )
            """
            async with conn.execute(query, (master_id, booking_date, start_time, start_time, end_time, end_time, start_time, end_time)) as cur:
                row = await cur.fetchone()
                if row["cnt"] > 0:
                    return None  # Slot already occupied

            cur = await conn.execute(
                """
                INSERT INTO bookings (client_id, service_id, master_id, booking_date, start_time, end_time, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
                """,
                (client_id, service_id, master_id, booking_date, start_time, end_time, notes)
            )
            await conn.commit()
            return cur.lastrowid

    async def get_booking_details(self, booking_id: int) -> Optional[Dict[str, Any]]:
        async with self.connect() as conn:
            query = """
            SELECT 
                b.id, b.booking_date, b.start_time, b.end_time, b.status, b.notes, b.created_at,
                c.telegram_id, c.full_name AS client_name, c.phone AS client_phone,
                s.name AS service_name, s.duration_minutes, s.price,
                m.name AS master_name, m.specialization AS master_spec
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            JOIN masters m ON b.master_id = m.id
            WHERE b.id = ?
            """
            async with conn.execute(query, (booking_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_client_bookings(self, telegram_id: int, only_upcoming: bool = True) -> List[Dict[str, Any]]:
        async with self.connect() as conn:
            query = """
            SELECT 
                b.id, b.booking_date, b.start_time, b.end_time, b.status,
                s.name AS service_name, s.price,
                m.name AS master_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            JOIN masters m ON b.master_id = m.id
            WHERE c.telegram_id = ?
            """
            if only_upcoming:
                query += " AND b.status = 'CONFIRMED' AND (b.booking_date > date('now') OR (b.booking_date = date('now') AND b.start_time >= time('now', 'localtime')))"
            query += " ORDER BY b.booking_date ASC, b.start_time ASC"

            async with conn.execute(query, (telegram_id,)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_master_bookings_for_date(self, master_id: int, booking_date: str) -> List[Dict[str, Any]]:
        async with self.connect() as conn:
            query = """
            SELECT start_time, end_time, status
            FROM bookings
            WHERE master_id = ? AND booking_date = ? AND status = 'CONFIRMED'
            ORDER BY start_time ASC
            """
            async with conn.execute(query, (master_id, booking_date)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_admin_bookings_report(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self.connect() as conn:
            query = """
            SELECT 
                b.id, b.booking_date, b.start_time, b.end_time, b.status,
                c.full_name AS client_name, c.phone AS client_phone, c.telegram_id,
                s.name AS service_name, s.price,
                m.name AS master_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            JOIN masters m ON b.master_id = m.id
            """
            params: Tuple[Any, ...] = ()
            if date_str:
                query += " WHERE b.booking_date = ? "
                params = (date_str,)
            query += " ORDER BY b.booking_date DESC, b.start_time ASC"

            async with conn.execute(query, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def cancel_booking(self, booking_id: int, client_telegram_id: Optional[int] = None) -> bool:
        async with self.connect() as conn:
            if client_telegram_id is not None:
                # Ensure client owns the booking
                check_query = """
                SELECT b.id FROM bookings b
                JOIN clients c ON b.client_id = c.id
                WHERE b.id = ? AND c.telegram_id = ? AND b.status = 'CONFIRMED'
                """
                async with conn.execute(check_query, (booking_id, client_telegram_id)) as cur:
                    if not await cur.fetchone():
                        return False

            await conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = ?", (booking_id,))
            await conn.commit()
            return True

    async def update_booking_status(self, booking_id: int, new_status: str) -> bool:
        async with self.connect() as conn:
            await conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
            await conn.commit()
            return True
