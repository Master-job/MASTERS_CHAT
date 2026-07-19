from aiogram.fsm.state import State, StatesGroup


class OrderSteps(StatesGroup):
    """Шаги квиза, который заполняет клиент."""
    entering_name = State()
    entering_phone = State()
    entering_address = State()
    entering_floor = State()
    choosing_elevator = State()
    choosing_service = State()
    entering_details = State()
    uploading_photo = State()
    entering_date = State()
    entering_time = State()
    entering_comment = State()
    confirming = State()
