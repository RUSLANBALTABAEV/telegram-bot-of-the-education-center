from aiogram.fsm.state import StatesGroup, State

class CourseFSM(StatesGroup):
    title = State()
    description = State()
    price = State()
