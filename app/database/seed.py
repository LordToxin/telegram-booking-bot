import logging
from app.database.db import Database

logger = logging.getLogger(__name__)


async def seed_initial_data(db: Database):
    """Populates default salon categories, services and masters if empty."""
    async with db.connect() as conn:
        async with conn.execute("SELECT COUNT(*) AS cnt FROM categories") as cur:
            row = await cur.fetchone()
            if row["cnt"] > 0:
                logger.info("Database already seeded. Skipping initial data.")
                return

        logger.info("Seeding initial database with salon services and masters...")

        # Categories
        categories = [
            ("💇‍♀️ Парикмахерские услуги", "💇‍♀️"),
            ("💅 Ногтевой сервис", "💅"),
            ("💆‍♀️ Косметология и уход", "💆‍♀️"),
            ("🧔 Барбершоп", "🧔")
        ]
        for name, icon in categories:
            await conn.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon))
        await conn.commit()

        # Fetch category IDs
        cat_map = {}
        async with conn.execute("SELECT id, name FROM categories") as cur:
            for row in await cur.fetchall():
                cat_map[row["name"]] = row["id"]

        # Services
        services = [
            # Hair
            (cat_map["💇‍♀️ Парикмахерские услуги"], "Женская стрижка + укладка", 60, 2500.0, "Мытье головы, модельная стрижка, сушка брашингом"),
            (cat_map["💇‍♀️ Парикмахерские услуги"], "Сложное окрашивание (Airtouch/Balayage)", 180, 7500.0, "Осветление по современным техникам, тонирование, глубокий уход"),
            (cat_map["💇‍♀️ Парикмахерские услуги"], "Ботокс для волос / Кератин", 120, 4500.0, "Восстановление структуры, термозащита, идеальная гладкость"),

            # Nails
            (cat_map["💅 Ногтевой сервис"], "Маникюр с покрытием гель-лак", 90, 2200.0, "Снятие, аппаратный/комбинированный маникюр, выравнивание, покрытие"),
            (cat_map["💅 Ногтевой сервис"], "Smart-педикюр полный", 90, 3000.0, "Обработка стоп smart-дисками, пальчики, покрытие гель-лак"),
            (cat_map["💅 Ногтевой сервис"], "Японский эко-маникюр Masura", 60, 1800.0, "Глянцевание пастой и пудрой из пчелиного воска"),

            # Cosmetology
            (cat_map["💆‍♀️ Косметология и уход"], "Ультразвуковая чистка лица", 60, 3200.0, "Демакияж, пилинг, УЗ-очищение, успокаивающая маска"),
            (cat_map["💆‍♀️ Косметология и уход"], "Массаж лица + альгинатная маска", 60, 2800.0, "Скульптурирующий лифтинг-массаж лица, шеи и декольте"),

            # Barber
            (cat_map["🧔 Барбершоп"], "Мужская стрижка Fade", 45, 1800.0, "Стрижка машинкой и ножницами, мытье, укладка премиум-стайлингом"),
            (cat_map["🧔 Барбершоп"], "Моделирование бороды с распариванием", 45, 1400.0, "Контуринг шаветкой, горячее полотенце, масло для бороды"),
        ]
        for cat_id, name, duration, price, desc in services:
            await conn.execute(
                "INSERT INTO services (category_id, name, duration_minutes, price, description) VALUES (?, ?, ?, ?, ?)",
                (cat_id, name, duration, price, desc)
            )

        # Masters
        masters = [
            ("Анна Соколова", "Топ-стилист / Колорист", "+7 (999) 111-22-33"),
            ("Елена Морозова", "Мастер ногтевого сервиса", "+7 (999) 444-55-66"),
            ("Дмитрий Волков", "Барбер / Мужской мастер", "+7 (999) 777-88-99"),
            ("Кристина Белова", "Косметолог-эстетист", "+7 (999) 333-22-11")
        ]
        for name, spec, phone in masters:
            await conn.execute(
                "INSERT INTO masters (name, specialization, phone) VALUES (?, ?, ?)",
                (name, spec, phone)
            )

        await conn.commit()
        logger.info("Initial data successfully seeded!")
