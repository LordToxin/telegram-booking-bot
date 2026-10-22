import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.db import Database
from app.services.booking_service import BookingService
from app.services.notification import NotificationService
from app.states.booking_states import BookingStates
from app.keyboards.client_kb import (
    get_main_menu_keyboard,
    get_categories_keyboard,
    get_services_keyboard,
    get_masters_keyboard,
    get_dates_keyboard,
    get_time_slots_keyboard,
    get_phone_request_keyboard,
    get_booking_confirmation_keyboard,
    get_my_bookings_keyboard
)

logger = logging.getLogger(__name__)
router = Router(name="client_router")


# --- START BOOKING WIZARD ---
@router.message(F.text == "📅 Записаться на услугу")
async def start_booking_flow(message: Message, state: FSMContext, db: Database):
    await state.clear()
    categories = await db.get_categories()
    if not categories:
        await message.answer("В данный момент нет доступных категорий услуг. Пожалуйста, обратитесь позже.")
        return

    await state.set_state(BookingStates.select_category)
    await message.answer(
        "🌸 <b>Шаг 1 из 5:</b> Выберите категорию услуг:",
        reply_markup=get_categories_keyboard(categories),
        parse_mode="HTML"
    )


# --- CATEGORY SELECTED ---
@router.callback_query(BookingStates.select_category, F.data.startswith("cat:"))
async def on_category_selected(call: CallbackQuery, state: FSMContext, db: Database):
    cat_id = int(call.data.split(":")[1])
    services = await db.get_services_by_category(cat_id)

    if not services:
        await call.answer("В этой категории пока нет доступных услуг.", show_alert=True)
        return

    await state.update_data(category_id=cat_id)
    await state.set_state(BookingStates.select_service)

    cat = await db.get_category(cat_id)
    await call.message.edit_text(
        f"💅 <b>Шаг 2 из 5:</b> Выберите услугу в категории <b>{cat.name if cat else ''}</b>:",
        reply_markup=get_services_keyboard(services),
        parse_mode="HTML"
    )
    await call.answer()


# --- BACK TO CATEGORIES ---
@router.callback_query(F.data == "nav:back_to_cats")
async def nav_back_to_cats(call: CallbackQuery, state: FSMContext, db: Database):
    categories = await db.get_categories()
    await state.set_state(BookingStates.select_category)
    await call.message.edit_text(
        "🌸 <b>Шаг 1 из 5:</b> Выберите категорию услуг:",
        reply_markup=get_categories_keyboard(categories),
        parse_mode="HTML"
    )
    await call.answer()


# --- SERVICE SELECTED ---
@router.callback_query(BookingStates.select_service, F.data.startswith("srv:"))
async def on_service_selected(call: CallbackQuery, state: FSMContext, db: Database):
    service_id = int(call.data.split(":")[1])
    service = await db.get_service(service_id)
    if not service:
        await call.answer("Услуга не найдена", show_alert=True)
        return

    masters = await db.get_active_masters()
    if not masters:
        await call.answer("Нет доступных специалистов.", show_alert=True)
        return

    await state.update_data(service_id=service_id, service_name=service.name, duration=service.duration_minutes, price=service.price)
    await state.set_state(BookingStates.select_master)

    await call.message.edit_text(
        f"💇 <b>Услуга:</b> {service.name}\n"
        f"⏱ <b>Длительность:</b> {service.duration_minutes} мин\n"
        f"💰 <b>Стоимость:</b> {service.price:,.0f} ₽\n\n"
        f"👤 <b>Шаг 3 из 5:</b> Выберите специалиста:",
        reply_markup=get_masters_keyboard(masters),
        parse_mode="HTML"
    )
    await call.answer()


# --- BACK TO SERVICES ---
@router.callback_query(F.data == "nav:back_to_services")
async def nav_back_to_services(call: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    cat_id = data.get("category_id")
    if not cat_id:
        return await start_booking_flow(call.message, state, db)

    services = await db.get_services_by_category(cat_id)
    await state.set_state(BookingStates.select_service)
    await call.message.edit_text(
        "💅 <b>Шаг 2 из 5:</b> Выберите услугу:",
        reply_markup=get_services_keyboard(services),
        parse_mode="HTML"
    )
    await call.answer()


# --- MASTER SELECTED ---
@router.callback_query(BookingStates.select_master, F.data.startswith("mstr:"))
async def on_master_selected(call: CallbackQuery, state: FSMContext, db: Database):
    master_id = int(call.data.split(":")[1])
    master = await db.get_master(master_id)
    if not master:
        await call.answer("Мастер не найден", show_alert=True)
        return

    await state.update_data(master_id=master_id, master_name=master.name)
    await state.set_state(BookingStates.select_date)

    upcoming_dates = BookingService.get_upcoming_dates(days_ahead=12)
    await call.message.edit_text(
        f"👤 <b>Специалист:</b> {master.name} ({master.specialization})\n\n"
        f"📅 <b>Шаг 4 из 5:</b> Выберите удобную дату визита:",
        reply_markup=get_dates_keyboard(upcoming_dates),
        parse_mode="HTML"
    )
    await call.answer()


# --- BACK TO MASTERS ---
@router.callback_query(F.data == "nav:back_to_masters")
async def nav_back_to_masters(call: CallbackQuery, state: FSMContext, db: Database):
    masters = await db.get_active_masters()
    await state.set_state(BookingStates.select_master)
    await call.message.edit_text(
        "👤 <b>Шаг 3 из 5:</b> Выберите специалиста:",
        reply_markup=get_masters_keyboard(masters),
        parse_mode="HTML"
    )
    await call.answer()


# --- DATE SELECTED ---
@router.callback_query(BookingStates.select_date, F.data.startswith("date:"))
async def on_date_selected(call: CallbackQuery, state: FSMContext, db: Database):
    date_str = call.data.split(":")[1]
    data = await state.get_data()
    master_id = data["master_id"]
    duration = data["duration"]

    booking_service = BookingService(db)
    slots = await booking_service.get_available_slots(master_id, date_str, duration)

    await state.update_data(booking_date=date_str)
    await state.set_state(BookingStates.select_time)

    await call.message.edit_text(
        f"📅 <b>Дата:</b> {date_str}\n\n"
        f"⏰ <b>Шаг 5 из 5:</b> Выберите подходящее время начала сеанса:",
        reply_markup=get_time_slots_keyboard(slots),
        parse_mode="HTML"
    )
    await call.answer()


# --- BACK TO DATES ---
@router.callback_query(F.data == "nav:back_to_dates")
async def nav_back_to_dates(call: CallbackQuery, state: FSMContext):
    upcoming_dates = BookingService.get_upcoming_dates(days_ahead=12)
    await state.set_state(BookingStates.select_date)
    await call.message.edit_text(
        "📅 <b>Шаг 4 из 5:</b> Выберите удобную дату визита:",
        reply_markup=get_dates_keyboard(upcoming_dates),
        parse_mode="HTML"
    )
    await call.answer()


# --- TIME SLOT SELECTED ---
@router.callback_query(BookingStates.select_time, F.data.startswith("time:"))
async def on_time_selected(call: CallbackQuery, state: FSMContext, db: Database):
    time_slot = call.data.split(":")[1]
    await state.update_data(start_time=time_slot)

    # Check if client already exists in DB
    existing_client = await db.get_client_by_telegram_id(call.from_user.id)
    if existing_client and existing_client.full_name and existing_client.phone:
        await state.update_data(
            client_name=existing_client.full_name,
            client_phone=existing_client.phone
        )
        await state.set_state(BookingStates.confirm_booking)
        data = await state.get_data()

        summary_text = (
            f"📋 <b>Пожалуйста, проверьте детали вашей записи:</b>\n\n"
            f"💇 <b>Услуга:</b> {data['service_name']}\n"
            f"💰 <b>Стоимость:</b> {data['price']:,.0f} ₽\n"
            f"👤 <b>Специалист:</b> {data['master_name']}\n"
            f"📅 <b>Дата:</b> {data['booking_date']}\n"
            f"⏰ <b>Время начала:</b> {data['start_time']}\n"
            f"👤 <b>Клиент:</b> {existing_client.full_name}\n"
            f"📞 <b>Телефон:</b> {existing_client.phone}\n\n"
            f"Все верно?"
        )
        await call.message.edit_text(
            summary_text,
            reply_markup=get_booking_confirmation_keyboard(),
            parse_mode="HTML"
        )
        await call.answer()
        return

    # If new client, ask for Name
    await state.set_state(BookingStates.enter_name)
    await call.message.delete()
    await call.message.answer(
        "✍️ Пожалуйста, введите ваше <b>Имя и Фамилию</b>:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await call.answer()


# --- ENTER NAME ---
@router.message(BookingStates.enter_name)
async def on_name_entered(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя (не менее 2 символов):")
        return

    await state.update_data(client_name=name)
    await state.set_state(BookingStates.enter_phone)

    await message.answer(
        f"Приятно познакомиться, {name}! 😊\n"
        f"Теперь укажите ваш номер телефона для подтверждения записи (нажмите кнопку ниже или введите вручную):",
        reply_markup=get_phone_request_keyboard()
    )


# --- ENTER PHONE ---
@router.message(BookingStates.enter_phone, F.contact)
@router.message(BookingStates.enter_phone, F.text)
async def on_phone_entered(message: Message, state: FSMContext):
    if message.text == "⬅️ Отмена":
        await state.clear()
        is_admin = message.from_user.id in settings.ADMIN_IDS
        await message.answer("Запись отменена.", reply_markup=get_main_menu_keyboard(is_admin=is_admin))
        return

    phone = message.contact.phone_number if message.contact else message.text.strip()
    # Basic phone cleanup
    clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if len(clean_phone) < 6:
        await message.answer("Пожалуйста, введите корректный номер телефона (например, +79991234567):")
        return

    await state.update_data(client_phone=clean_phone)
    await state.set_state(BookingStates.confirm_booking)

    data = await state.get_data()
    summary_text = (
        f"📋 <b>Пожалуйста, проверьте детали вашей записи:</b>\n\n"
        f"💇 <b>Услуга:</b> {data['service_name']}\n"
        f"💰 <b>Стоимость:</b> {data['price']:,.0f} ₽\n"
        f"👤 <b>Специалист:</b> {data['master_name']}\n"
        f"📅 <b>Дата:</b> {data['booking_date']}\n"
        f"⏰ <b>Время начала:</b> {data['start_time']}\n"
        f"👤 <b>Клиент:</b> {data['client_name']}\n"
        f"📞 <b>Телефон:</b> {data['client_phone']}\n\n"
        f"Все верно?"
    )

    is_admin = message.from_user.id in settings.ADMIN_IDS
    await message.answer("Данные сохранены.", reply_markup=get_main_menu_keyboard(is_admin=is_admin))
    await message.answer(
        summary_text,
        reply_markup=get_booking_confirmation_keyboard(),
        parse_mode="HTML"
    )


# --- CONFIRM BOOKING ---
@router.callback_query(BookingStates.confirm_booking, F.data == "confirm:yes")
async def on_booking_confirmed(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    notification_service: NotificationService
):
    data = await state.get_data()
    booking_service = BookingService(db)

    success, booking_id, msg = await booking_service.book_appointment(
        telegram_id=call.from_user.id,
        full_name=data["client_name"],
        phone=data["client_phone"],
        service_id=data["service_id"],
        master_id=data["master_id"],
        booking_date=data["booking_date"],
        start_time=data["start_time"]
    )

    if not success:
        await call.answer(msg, show_alert=True)
        await state.clear()
        return

    # Fetch booking details for notifications
    booking_details = await db.get_booking_details(booking_id)
    if booking_details:
        booking_details["username"] = call.from_user.username
        await notification_service.notify_admins_new_booking(booking_details)

    await state.clear()
    is_admin = call.from_user.id in settings.ADMIN_IDS

    success_text = (
        f"🎉 <b>Вы успешно записаны!</b>\n\n"
        f"🔖 <b>Номер записи:</b> #{booking_id}\n"
        f"💇 <b>Услуга:</b> {data['service_name']}\n"
        f"👤 <b>Мастер:</b> {data['master_name']}\n"
        f"📅 <b>Дата и время:</b> {data['booking_date']} в {data['start_time']}\n"
        f"📍 <b>Адрес:</b> {settings.SALON_ADDRESS}\n\n"
        f"Мы ждем вас! Если ваши планы изменятся, вы можете отменить запись в разделе <b>📋 Мои записи</b>."
    )

    await call.message.edit_text(success_text, parse_mode="HTML")
    await call.answer("Запись подтверждена!")


# --- MY BOOKINGS ---
@router.message(F.text == "📋 Мои записи")
async def show_my_bookings(message: Message, db: Database):
    bookings = await db.get_client_bookings(message.from_user.id, only_upcoming=True)
    if not bookings:
        await message.answer(
            "У вас пока нет активных записей.\n"
            "Чтобы выбрать удобное время, нажмите <b>📅 Записаться на услугу</b>.",
            parse_mode="HTML"
        )
        return

    text_parts = ["📋 <b>Ваши актуальные записи:</b>\n"]
    for b in bookings:
        text_parts.append(
            f"• <b>#{b['id']}</b>: 📅 <b>{b['booking_date']} в {b['start_time']}</b>\n"
            f"   💇 {b['service_name']} ({b['price']:,.0f} ₽)\n"
            f"   👤 Мастер: {b['master_name']}\n"
        )
    text_parts.append("\nЧтобы отменить визит, нажмите кнопку ниже:")

    await message.answer(
        "\n".join(text_parts),
        reply_markup=get_my_bookings_keyboard(bookings),
        parse_mode="HTML"
    )


# --- CANCEL BOOKING ---
@router.callback_query(F.data.startswith("cancel_booking:"))
async def on_cancel_booking(
    call: CallbackQuery,
    db: Database,
    notification_service: NotificationService
):
    booking_id = int(call.data.split(":")[1])
    booking_info = await db.get_booking_details(booking_id)

    success = await db.cancel_booking(booking_id, client_telegram_id=call.from_user.id)
    if not success:
        await call.answer("Не удалось отменить запись или она уже была отменена.", show_alert=True)
        return

    if booking_info:
        await notification_service.notify_admins_cancelled_booking(booking_info)

    await call.message.edit_text(
        f"✅ <b>Запись #{booking_id} успешно отменена.</b>\n"
        f"Слот освобожден. Вы всегда можете записаться снова в любое время!",
        parse_mode="HTML"
    )
    await call.answer("Запись отменена")
