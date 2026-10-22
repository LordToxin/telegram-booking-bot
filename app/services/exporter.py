import csv
import io
from typing import List, Dict, Any


class ExporterService:
    @staticmethod
    def export_bookings_to_csv(bookings: List[Dict[str, Any]]) -> io.BytesIO:
        """
        Exports a list of bookings dicts to an in-memory CSV UTF-8-sig (Excel compatible) buffer.
        """
        output = io.StringIO()
        fieldnames = [
            "ID записи",
            "Дата",
            "Время начала",
            "Время окончания",
            "Клиент",
            "Телефон",
            "Telegram ID",
            "Услуга",
            "Стоимость (руб)",
            "Специалист",
            "Статус"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()

        for b in bookings:
            writer.writerow({
                "ID записи": b.get("id"),
                "Дата": b.get("booking_date"),
                "Время начала": b.get("start_time"),
                "Время окончания": b.get("end_time"),
                "Клиент": b.get("client_name"),
                "Телефон": b.get("client_phone"),
                "Telegram ID": b.get("telegram_id"),
                "Услуга": b.get("service_name"),
                "Стоимость (руб)": b.get("price"),
                "Специалист": b.get("master_name"),
                "Статус": b.get("status")
            })

        # Return utf-8-sig encoded bytes for correct Russian chars in Microsoft Excel
        bytes_io = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        bytes_io.seek(0)
        return bytes_io
