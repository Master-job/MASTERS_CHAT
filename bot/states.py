from aiogram.fsm.state import State, StatesGroup

class OrderSteps(StatesGroup):
    entering_name = State()
    entering_phone = State()
    choosing_service = State()      # Шаг 1
    choosing_amount = State()       # Шаг 2
    choosing_condition = State()    # Шаг 3
    uploading_photo = State()       # Шаг 4
    choosing_location = State()     # Шаг 5 (Москва/МО)
    entering_district = State()     # Шаг 5 (Район)
    choosing_timing = State()       # Шаг 6
    confirming = State()