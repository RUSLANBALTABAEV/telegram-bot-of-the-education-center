from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    name = State()
    age = State()
    phone = State()
    photo = State()
    document = State()
