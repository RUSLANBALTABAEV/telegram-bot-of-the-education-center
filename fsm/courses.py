from aiogram.fsm.state import StatesGroup, State

class CourseFSM(StatesGroup):
    choosing_course = State()
