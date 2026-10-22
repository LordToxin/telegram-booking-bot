import pytest
import pytest_asyncio
from pathlib import Path
from app.database.db import Database
from app.database.seed import seed_initial_data
from app.services.booking_service import BookingService


@pytest_asyncio.fixture
async def service_and_db(tmp_path: Path):
    db_file = tmp_path / "test_svc.db"
    db = Database(db_file)
    await db.init_tables()
    await seed_initial_data(db)
    service = BookingService(db)
    return service, db


@pytest.mark.asyncio
async def test_calculate_end_time():
    end = BookingService.calculate_end_time("14:00", 90)
    assert end == "15:30"
    end2 = BookingService.calculate_end_time("10:15", 45)
    assert end2 == "11:00"


@pytest.mark.asyncio
async def test_get_upcoming_dates():
    dates = BookingService.get_upcoming_dates(7)
    assert len(dates) == 7
    assert "Сегодня" in dates[0][1]
    assert "Завтра" in dates[1][1]


@pytest.mark.asyncio
async def test_available_slots_computation(service_and_db):
    service, db = service_and_db
    test_date = "2026-12-01"  # future date

    # Initial slots: with open=10, close=20, duration=60, step=30
    slots_initial = await service.get_available_slots(master_id=1, date_str=test_date, duration_minutes=60)
    assert "10:00" in slots_initial
    assert "14:00" in slots_initial

    # Book 14:00 to 15:00
    client = await db.get_or_create_client(111, "Тест", "+79991112233")
    await db.create_booking(
        client_id=client.id,
        service_id=1,
        master_id=1,
        booking_date=test_date,
        start_time="14:00",
        end_time="15:00"
    )

    # Re-calculate slots
    slots_after = await service.get_available_slots(master_id=1, date_str=test_date, duration_minutes=60)
    assert "14:00" not in slots_after, "14:00 must be unavailable as it's booked!"
    assert "13:30" not in slots_after, "13:30 (ending at 14:30) must overlap with 14:00-15:00!"
    assert "15:00" in slots_after, "15:00 should be free!"
