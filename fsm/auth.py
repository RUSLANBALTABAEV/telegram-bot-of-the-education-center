from aiogram.fsm.state import StatesGroup, State


class Auth(StatesGroup):
    phone = State()
