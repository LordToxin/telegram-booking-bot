import pytest
import pytest_asyncio
import os
from pathlib import Path
from app.database.db import Database
from app.database.seed import seed_initial_data


@pytest_asyncio.fixture
async def test_db(tmp_path: Path):
    db_file = tmp_path / "test_booking.db"
    db = Database(db_file)
    await db.init_tables()
    await seed_initial_data(db)
    yield db


@pytest.mark.asyncio
async def test_db_seeding_and_categories(test_db: Database):
    categories = await test_db.get_categories()
    assert len(categories) >= 4
    cat_names = [c.name for c in categories]
    assert any("Парикмахерские" in name for name in cat_names)

    # Services under category 1
    services = await test_db.get_services_by_category(categories[0].id)
    assert len(services) > 0
    assert services[0].price > 0


@pytest.mark.asyncio
async def test_client_creation(test_db: Database):
    client = await test_db.get_or_create_client(
        telegram_id=999888777,
        full_name="Иван Иванов",
        phone="+79991112233"
    )
    assert client.id is not None
    assert client.full_name == "Иван Иванов"

    # Fetch again - should return the same client without duplicate
    client2 = await test_db.get_or_create_client(
        telegram_id=999888777,
        full_name="Иван Иванов",
        phone="+79991112233"
    )
    assert client2.id == client.id


@pytest.mark.asyncio
async def test_booking_creation_and_collision(test_db: Database):
    client = await test_db.get_or_create_client(123456, "Анна Петрова", "+79998887766")
    masters = await test_db.get_active_masters()
    services = await test_db.get_services_by_category(1)

    master = masters[0]
    service = services[0]

    # Create first booking: 12:00 to 13:00
    booking_id = await test_db.create_booking(
        client_id=client.id,
        service_id=service.id,
        master_id=master.id,
        booking_date="2026-11-01",
        start_time="12:00",
        end_time="13:00"
    )
    assert booking_id is not None

    # Collision test: attempt booking overlapping 12:30 to 13:30 with same master
    colliding_id = await test_db.create_booking(
        client_id=client.id,
        service_id=service.id,
        master_id=master.id,
        booking_date="2026-11-01",
        start_time="12:30",
        end_time="13:30"
    )
    assert colliding_id is None, "Should reject overlapping booking for the same master!"

    # Non-overlapping booking: 13:00 to 14:00 with same master should succeed
    next_booking_id = await test_db.create_booking(
        client_id=client.id,
        service_id=service.id,
        master_id=master.id,
        booking_date="2026-11-01",
        start_time="13:00",
        end_time="14:00"
    )
    assert next_booking_id is not None


@pytest.mark.asyncio
async def test_booking_cancellation(test_db: Database):
    client = await test_db.get_or_create_client(777, "Сергей Смирнов", "+79990001122")
    booking_id = await test_db.create_booking(
        client_id=client.id,
        service_id=1,
        master_id=1,
        booking_date="2026-11-05",
        start_time="15:00",
        end_time="16:00"
    )
    assert booking_id is not None

    # Cancel by client
    success = await test_db.cancel_booking(booking_id, client_telegram_id=777)
    assert success is True

    # Details check
    details = await test_db.get_booking_details(booking_id)
    assert details["status"] == "CANCELLED"
