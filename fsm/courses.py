from aiogram.fsm.state import StatesGroup, State


class CourseFSM(StatesGroup):
    choosing_course = State()
    unsubscribe_course = State()   # состояние для отписки
