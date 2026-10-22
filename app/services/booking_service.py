from datetime import datetime, date, time, timedelta
from typing import List, Tuple, Dict, Any, Optional
from app.config import settings
from app.database.db import Database


class BookingService:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def get_upcoming_dates(days_ahead: int = 14) -> List[Tuple[str, str]]:
        """
        Returns list of (date_iso, display_label), e.g.
        [('2026-10-22', 'Сегодня, 22 окт'), ('2026-10-23', 'Завтра, 23 окт'), ...]
        """
        months_ru = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "мая", 6: "июн",
            7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"
        }
        weekdays_ru = {
            0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"
        }

        today = date.today()
        dates = []
        for i in range(days_ahead):
            d = today + timedelta(days=i)
            iso = d.strftime("%Y-%m-%d")
            m_name = months_ru[d.month]
            w_name = weekdays_ru[d.weekday()]

            if i == 0:
                label = f"Сегодня ({d.day} {m_name})"
            elif i == 1:
                label = f"Завтра ({d.day} {m_name})"
            else:
                label = f"{w_name}, {d.day} {m_name}"
            dates.append((iso, label))
        return dates

    @staticmethod
    def calculate_end_time(start_time_str: str, duration_minutes: int) -> str:
        """Calculates end_time string (HH:MM) from start_time (HH:MM) and duration."""
        h, m = map(int, start_time_str.split(":"))
        dt = datetime(2000, 1, 1, h, m) + timedelta(minutes=duration_minutes)
        return dt.strftime("%H:%M")

    @staticmethod
    def _is_overlapping(start1: str, end1: str, start2: str, end2: str) -> bool:
        """Returns True if time interval [start1, end1] overlaps with [start2, end2]."""
        return not (end1 <= start2 or start1 >= end2)

    async def get_available_slots(
        self,
        master_id: int,
        date_str: str,
        duration_minutes: int
    ) -> List[str]:
        """
        Calculates all free time slots for a given master on a specific date.
        """
        open_h = settings.SALON_OPEN_HOUR
        close_h = settings.SALON_CLOSE_HOUR
        step = settings.SLOT_STEP_MINUTES

        # Fetch existing confirmed bookings for the master on this date
        existing_bookings = await self.db.get_master_bookings_for_date(master_id, date_str)

        available_slots = []
        current_time = datetime.strptime(f"{open_h:02d}:00", "%H:%M")
        close_time = datetime.strptime(f"{close_h:02d}:00", "%H:%M")

        # Check against now if date is today
        now = datetime.now()
        is_today = (date_str == now.strftime("%Y-%m-%d"))

        while current_time + timedelta(minutes=duration_minutes) <= close_time:
            slot_start = current_time.strftime("%H:%M")
            slot_end = (current_time + timedelta(minutes=duration_minutes)).strftime("%H:%M")

            # If today, skip if slot has already passed (+15 min buffer)
            if is_today:
                cur_slot_dt = datetime.strptime(f"{date_str} {slot_start}", "%Y-%m-%d %H:%M")
                if cur_slot_dt <= now + timedelta(minutes=15):
                    current_time += timedelta(minutes=step)
                    continue

            # Check collision with existing bookings
            conflict = False
            for b in existing_bookings:
                if self._is_overlapping(slot_start, slot_end, b["start_time"], b["end_time"]):
                    conflict = True
                    break

            if not conflict:
                available_slots.append(slot_start)

            current_time += timedelta(minutes=step)

        return available_slots

    async def book_appointment(
        self,
        telegram_id: int,
        full_name: str,
        phone: str,
        service_id: int,
        master_id: int,
        booking_date: str,
        start_time: str,
        notes: str = ""
    ) -> Tuple[bool, Optional[int], str]:
        """
        Creates client and atomic booking.
        Returns: (success, booking_id, message)
        """
        service = await self.db.get_service(service_id)
        if not service:
            return False, None, "Услуга не найдена"

        end_time = self.calculate_end_time(start_time, service.duration_minutes)

        client = await self.db.get_or_create_client(telegram_id, full_name, phone)

        booking_id = await self.db.create_booking(
            client_id=client.id,
            service_id=service_id,
            master_id=master_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            notes=notes
        )

        if not booking_id:
            return False, None, "Выбранное время уже занято другим клиентом. Пожалуйста, выберите другой слот."

        return True, booking_id, "Успешно забронировано"
