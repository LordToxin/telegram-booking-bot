from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    select_category = State()
    select_service = State()
    select_master = State()
    select_date = State()
    select_time = State()
    enter_name = State()
    enter_phone = State()
    confirm_booking = State()


class AdminStates(StatesGroup):
    broadcast_message = State()
    add_service_category = State()
    add_service_name = State()
    add_service_duration = State()
    add_service_price = State()
