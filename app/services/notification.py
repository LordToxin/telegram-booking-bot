import logging
from typing import Dict, Any
from aiogram import Bot
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_admins_new_booking(self, booking_info: Dict[str, Any]):
        """Notifies all configured admins about a new customer appointment."""
        text = (
            f"🔔 <b>Новая запись в салон!</b>\n\n"
            f"📅 <b>Дата:</b> {booking_info['booking_date']}\n"
            f"⏰ <b>Время:</b> {booking_info['start_time']} - {booking_info['end_time']}\n"
            f"💇 <b>Услуга:</b> {booking_info['service_name']} ({booking_info['price']:,.0f} ₽)\n"
            f"👤 <b>Специалист:</b> {booking_info['master_name']}\n"
            f"👤 <b>Клиент:</b> {booking_info['client_name']}\n"
            f"📞 <b>Телефон:</b> {booking_info['client_phone']}\n"
            f"🆔 <b>Telegram:</b> @{booking_info.get('username') or 'без username'} (ID: {booking_info['telegram_id']})"
        )

        for admin_id in settings.ADMIN_IDS:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed to send admin notification to {admin_id}: {e}")

    async def notify_admins_cancelled_booking(self, booking_info: Dict[str, Any]):
        """Notifies admins when a customer cancels their appointment."""
        text = (
            f"❌ <b>Отмена записи #{booking_info['id']}!</b>\n\n"
            f"📅 <b>Дата:</b> {booking_info['booking_date']} {booking_info['start_time']}\n"
            f"💇 <b>Услуга:</b> {booking_info['service_name']}\n"
            f"👤 <b>Специалист:</b> {booking_info['master_name']}\n"
            f"👤 <b>Клиент:</b> {booking_info['client_name']} ({booking_info['client_phone']})\n"
            f"ℹ️ Слот освобожден для других клиентов."
        )

        for admin_id in settings.ADMIN_IDS:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed to send cancellation notification to {admin_id}: {e}")
