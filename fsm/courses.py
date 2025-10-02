# ============ fsm/courses.py ============
"""
FSM состояния для добавления курса (не используется в текущей версии).
"""
from aiogram.fsm.state import StatesGroup, State


class CourseFSM(StatesGroup):
    """Состояния для добавления курса."""
    title = State()
    description = State()
    price = State()
