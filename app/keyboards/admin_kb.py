from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.models import Category


def get_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записи на сегодня", callback_data="admin:today")
    builder.button(text="🗓 Все предстоящие записи", callback_data="admin:upcoming")
    builder.button(text="📥 Экспорт в Excel (CSV)", callback_data="admin:export")
    builder.button(text="➕ Добавить услугу", callback_data="admin:add_service")
    builder.button(text="📢 Рассылка всем клиентам", callback_data="admin:broadcast")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat.icon} {cat.name}", callback_data=f"adm_cat:{cat.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel"))
    return builder.as_markup()


def get_booking_manage_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершить", callback_data=f"adm_status:{booking_id}:COMPLETED")
    builder.button(text="❌ Отменить", callback_data=f"adm_status:{booking_id}:CANCELLED")
    builder.adjust(2)
    return builder.as_markup()
