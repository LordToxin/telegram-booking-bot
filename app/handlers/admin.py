import logging
from datetime import datetime, date
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.db import Database
from app.services.exporter import ExporterService
from app.states.booking_states import AdminStates
from app.keyboards.admin_kb import (
    get_admin_dashboard_keyboard,
    get_admin_categories_keyboard,
    get_booking_manage_keyboard
)

logger = logging.getLogger(__name__)
router = Router(name="admin_router")


def is_admin_check(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# --- ADMIN DASHBOARD ---
@router.message(Command("admin"))
@router.message(F.text == "⚙️ Панель администратора")
async def show_admin_dashboard(message: Message, state: FSMContext, db: Database):
    if not is_admin_check(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к панели администратора.")
        return

    await state.clear()
    today_str = date.today().strftime("%Y-%m-%d")
    today_bookings = await db.get_admin_bookings_report(date_str=today_str)
    all_clients = await db.get_all_clients()

    confirmed_today = [b for b in today_bookings if b["status"] == "CONFIRMED"]

    text = (
        f"👑 <b>Панель управления салоном:</b> {settings.SALON_NAME}\n\n"
        f"📅 <b>Сегодня ({today_str}):</b> {len(confirmed_today)} активных записей\n"
        f"👥 <b>Всего клиентов в базе:</b> {len(all_clients)}\n\n"
        f"Выберите раздел для управления:"
    )

    await message.answer(text, reply_markup=get_admin_dashboard_keyboard(), parse_mode="HTML")


# --- TODAY'S BOOKINGS ---
@router.callback_query(F.data == "admin:today")
async def on_admin_today(call: CallbackQuery, db: Database):
    if not is_admin_check(call.from_user.id):
        return

    today_str = date.today().strftime("%Y-%m-%d")
    bookings = await db.get_admin_bookings_report(date_str=today_str)

    if not bookings:
        await call.message.edit_text(
            f"📅 На сегодня ({today_str}) записей нет.",
            reply_markup=get_admin_dashboard_keyboard()
        )
        await call.answer()
        return

    text_parts = [f"📅 <b>Записи на сегодня ({today_str}):</b>\n"]
    for b in bookings:
        status_emoji = "✅" if b["status"] == "CONFIRMED" else ("🏁" if b["status"] == "COMPLETED" else "❌")
        text_parts.append(
            f"{status_emoji} <b>#{b['id']}</b> [{b['start_time']} - {b['end_time']}]\n"
            f"   💇 {b['service_name']} ({b['price']:,.0f} ₽)\n"
            f"   👤 Мастер: {b['master_name']}\n"
            f"   👤 Клиент: {b['client_name']} ({b['client_phone']})\n"
        )

    await call.message.edit_text(
        "\n".join(text_parts),
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()


# --- UPCOMING BOOKINGS ---
@router.callback_query(F.data == "admin:upcoming")
async def on_admin_upcoming(call: CallbackQuery, db: Database):
    if not is_admin_check(call.from_user.id):
        return

    bookings = await db.get_admin_bookings_report()
    upcoming = [b for b in bookings if b["status"] == "CONFIRMED"][:15]

    if not upcoming:
        await call.message.edit_text(
            "🗓 Нет активных предстоящих записей.",
            reply_markup=get_admin_dashboard_keyboard()
        )
        await call.answer()
        return

    text_parts = ["🗓 <b>Ближайшие предстоящие записи (топ-15):</b>\n"]
    for b in upcoming:
        text_parts.append(
            f"• <b>#{b['id']}</b> | 📅 {b['booking_date']} {b['start_time']}\n"
            f"   💇 {b['service_name']} -> {b['master_name']}\n"
            f"   Клиент: {b['client_name']} ({b['client_phone']})\n"
        )

    await call.message.edit_text(
        "\n".join(text_parts),
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()


# --- EXPORT TO CSV / EXCEL ---
@router.callback_query(F.data == "admin:export")
async def on_admin_export(call: CallbackQuery, db: Database):
    if not is_admin_check(call.from_user.id):
        return

    await call.answer("Генерация выгрузки...")
    bookings = await db.get_admin_bookings_report()

    if not bookings:
        await call.message.answer("Записей для экспорта пока нет.")
        return

    csv_buffer = ExporterService.export_bookings_to_csv(bookings)
    file_bytes = csv_buffer.getvalue()

    filename = f"salon_bookings_{date.today().strftime('%Y%m%d')}.csv"
    input_file = BufferedInputFile(file=file_bytes, filename=filename)

    await call.message.answer_document(
        document=input_file,
        caption=f"📊 <b>Экспорт базы записей и клиентов салона</b>\nВсего записей: {len(bookings)}",
        parse_mode="HTML"
    )


# --- ADD SERVICE FLOW ---
@router.callback_query(F.data == "admin:add_service")
async def on_admin_add_service_start(call: CallbackQuery, state: FSMContext, db: Database):
    if not is_admin_check(call.from_user.id):
        return

    categories = await db.get_categories()
    await state.set_state(AdminStates.add_service_category)
    await call.message.edit_text(
        "➕ <b>Добавление новой услуги</b>\nВыберите категорию для услуги:",
        reply_markup=get_admin_categories_keyboard(categories),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(AdminStates.add_service_category, F.data.startswith("adm_cat:"))
async def on_admin_category_selected(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split(":")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminStates.add_service_name)
    await call.message.edit_text("Введите <b>название</b> новой услуги:\n(Например: <i>Вечерний макияж</i>)", parse_mode="HTML")
    await call.answer()


@router.message(AdminStates.add_service_name)
async def on_admin_service_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AdminStates.add_service_duration)
    await message.answer("Введите <b>длительность услуги в минутах</b>:\n(Например: <i>60</i>)", parse_mode="HTML")


@router.message(AdminStates.add_service_duration)
async def on_admin_service_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите положительное число (например, 45 или 60):")
        return

    await state.update_data(duration=duration)
    await state.set_state(AdminStates.add_service_price)
    await message.answer("Введите <b>стоимость услуги в рублях</b>:\n(Например: <i>3500</i>)", parse_mode="HTML")


@router.message(AdminStates.add_service_price)
async def on_admin_service_price(message: Message, state: FSMContext, db: Database):
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную цену (например, 2500):")
        return

    data = await state.get_data()
    service_id = await db.add_service(
        category_id=data["category_id"],
        name=data["name"],
        duration=data["duration"],
        price=price
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Услуга успешно добавлена!</b>\n\n"
        f"💅 <b>Название:</b> {data['name']}\n"
        f"⏱ <b>Длительность:</b> {data['duration']} мин\n"
        f"💰 <b>Цена:</b> {price:,.0f} ₽\n"
        f"ID в каталоге: #{service_id}",
        parse_mode="HTML"
    )


# --- BROADCAST FLOW ---
@router.callback_query(F.data == "admin:broadcast")
async def on_admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin_check(call.from_user.id):
        return

    await state.set_state(AdminStates.broadcast_message)
    await call.message.edit_text(
        "📢 <b>Рассылка сообщений клиентам</b>\n\n"
        "Отправьте текст сообщения для рассылки (акции, спецпредложения, анонсы).\n"
        "Для отмены отправьте /admin",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminStates.broadcast_message)
async def on_admin_broadcast_send(message: Message, state: FSMContext, db: Database, bot: Bot):
    clients = await db.get_all_clients()
    await state.clear()

    if not clients:
        await message.answer("В базе еще нет клиентов для рассылки.")
        return

    status_msg = await message.answer(f"⏳ Отправка рассылки {len(clients)} клиентам...")

    sent_count = 0
    fail_count = 0
    broadcast_text = f"📢 <b>Сообщение от салона {settings.SALON_NAME}:</b>\n\n{message.text}"

    for c in clients:
        try:
            await bot.send_message(chat_id=c.telegram_id, text=broadcast_text, parse_mode="HTML")
            sent_count += 1
        except Exception as e:
            logger.debug(f"Broadcast failed for {c.telegram_id}: {e}")
            fail_count += 1

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Успешно доставлено: {sent_count}\n"
        f"⚠️ Не доставлено (заблокировали бота): {fail_count}",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:cancel")
async def on_admin_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer("Действие отменено.", reply_markup=get_admin_dashboard_keyboard())
    await call.answer()
