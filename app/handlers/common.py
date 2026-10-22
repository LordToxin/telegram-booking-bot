from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.db import Database
from app.keyboards.client_kb import get_main_menu_keyboard

router = Router(name="common_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database):
    await state.clear()
    is_admin = message.from_user.id in settings.ADMIN_IDS

    welcome_text = (
        f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
        f"Добро пожаловать в <b>{settings.SALON_NAME}</b>.\n"
        f"Здесь вы можете быстро записаться к любимому мастеру в удобное для вас время без звонков и ожидания.\n\n"
        f"📍 <b>Адрес:</b> {settings.SALON_ADDRESS}\n"
        f"🕒 <b>Режим работы:</b> ежедневно с {settings.SALON_OPEN_HOUR}:00 до {settings.SALON_CLOSE_HOUR}:00\n"
        f"📞 <b>Телефон:</b> {settings.SALON_PHONE}\n\n"
        f"Выберите нужное действие в меню ниже 👇"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        f"📖 <b>Как пользоваться ботом {settings.SALON_NAME}:</b>\n\n"
        f"1. Нажмите кнопку <b>📅 Записаться на услугу</b>.\n"
        f"2. Выберите категорию, услугу и подходящего мастера.\n"
        f"3. Выберите удобную дату и время.\n"
        f"4. Укажите ваше имя и контактный телефон.\n"
        f"5. Подтвердите запись — бот мгновенно забронирует слот и пришлет вам напоминание.\n\n"
        f"В разделе <b>📋 Мои записи</b> вы всегда можете просмотреть свои бронирования или отменить визит.\n"
        f"По всем вопросам: {settings.SALON_PHONE}"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text == "📍 Контакты и адрес")
async def show_contacts(message: Message):
    contacts_text = (
        f"📍 <b>Салон красоты:</b> {settings.SALON_NAME}\n"
        f"🏢 <b>Адрес:</b> {settings.SALON_ADDRESS}\n"
        f"⏰ <b>Часы работы:</b> ежедневно {settings.SALON_OPEN_HOUR}:00 – {settings.SALON_CLOSE_HOUR}:00\n"
        f"📞 <b>Телефон для связи:</b> {settings.SALON_PHONE}\n"
        f"🚗 <b>Парковка:</b> бесплатная парковка для клиентов студии."
    )
    await message.answer(contacts_text, parse_mode="HTML")


@router.message(F.text == "💰 Прайс-лист")
async def show_price_list(message: Message, db: Database):
    categories = await db.get_categories()
    if not categories:
        await message.answer("Прайс-лист сейчас обновляется. Пожалуйста, обратитесь к администратору.")
        return

    text_parts = [f"✨ <b>Прайс-лист салона {settings.SALON_NAME}</b>\n"]
    for cat in categories:
        services = await db.get_services_by_category(cat.id)
        if services:
            text_parts.append(f"\n<b>{cat.icon} {cat.name}</b>")
            for s in services:
                text_parts.append(f"  • {s.name} — <b>{s.price:,.0f} ₽</b> <i>({s.duration_minutes} мин)</i>")

    text_parts.append("\nДля записи нажмите кнопку <b>📅 Записаться на услугу</b> в меню.")
    await message.answer("\n".join(text_parts), parse_mode="HTML")


@router.callback_query(F.data == "client:cancel")
async def callback_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = call.from_user.id in settings.ADMIN_IDS
    await call.message.delete()
    await call.message.answer(
        "Действие отменено. Вы вернулись в главное меню.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin)
    )
    await call.answer()
