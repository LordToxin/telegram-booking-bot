from app.services.exporter import ExporterService


def test_export_bookings_to_csv():
    mock_bookings = [
        {
            "id": 1,
            "booking_date": "2026-11-10",
            "start_time": "11:00",
            "end_time": "12:00",
            "client_name": "Алена Смирнова",
            "client_phone": "+79991234567",
            "telegram_id": 123456,
            "service_name": "Женская стрижка",
            "price": 2500.0,
            "master_name": "Анна Соколова",
            "status": "CONFIRMED"
        }
    ]

    csv_buffer = ExporterService.export_bookings_to_csv(mock_bookings)
    content = csv_buffer.getvalue().decode("utf-8-sig")

    assert "ID записи;Дата;Время начала" in content
    assert "Алена Смирнова" in content
    assert "+79991234567" in content
    assert "2500.0" in content
    assert "Женская стрижка" in content
