from typing import List, Tuple, Dict, Any
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.models import Category, Service, Master


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Returns main menu reply keyboard."""
    buttons = [
        [KeyboardButton(text="📅 Записаться на услугу"), KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="💰 Прайс-лист"), KeyboardButton(text="📍 Контакты и адрес")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="⚙️ Панель администратора")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat.icon} {cat.name}", callback_data=f"cat:{cat.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="client:cancel"))
    return builder.as_markup()


def get_services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(
            text=f"{s.name} • {s.price:,.0f} ₽ ({s.duration_minutes} мин)",
            callback_data=f"srv:{s.id}"
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="nav:back_to_cats"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="client:cancel")
    )
    return builder.as_markup()


def get_masters_keyboard(masters: List[Master]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in masters:
        builder.button(
            text=f"👤 {m.name} ({m.specialization})",
            callback_data=f"mstr:{m.id}"
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="nav:back_to_services"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="client:cancel")
    )
    return builder.as_markup()


def get_dates_keyboard(upcoming_dates: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for date_iso, label in upcoming_dates:
        builder.button(text=label, callback_data=f"date:{date_iso}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к специалистам", callback_data="nav:back_to_masters"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="client:cancel")
    )
    return builder.as_markup()


def get_time_slots_keyboard(slots: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not slots:
        builder.button(text="❌ Нет свободных мест на эту дату", callback_data="noop")
        builder.adjust(1)
    else:
        for slot in slots:
            builder.button(text=f"🕒 {slot}", callback_data=f"time:{slot}")
        builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="nav:back_to_dates"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="client:cancel")
    )
    return builder.as_markup()


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="⬅️ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_booking_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm:yes")
    builder.button(text="❌ Отменить", callback_data="client:cancel")
    builder.adjust(2)
    return builder.as_markup()


def get_my_bookings_keyboard(bookings: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        btn_text = f"❌ Отменить: {b['booking_date']} {b['start_time']} ({b['service_name']})"
        builder.button(text=btn_text, callback_data=f"cancel_booking:{b['id']}")
    builder.adjust(1)
    return builder.as_markup()
