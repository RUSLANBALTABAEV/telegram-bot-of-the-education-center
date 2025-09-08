# keyboards/reply.py
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config.bot_config import ADMIN_ID

def main_menu(user_id: int):
    """
    Возвращает клавиатуру — для админа и для обычного пользователя.
    Совместимо с остальными хендлерами (тексты кнопок совпадают).
    """

    builder = ReplyKeyboardBuilder()

    # добавляем кнопку "Старт" в начало
    builder.row(KeyboardButton(text="Старт"))

    # основные кнопки для всех
    builder.row(KeyboardButton(text="Регистрация"))
    builder.row(KeyboardButton(text="Авторизация"))
    builder.row(KeyboardButton(text="Курсы"))

    # безопасная проверка — ADMIN_ID может быть int или список/кортеж/строка с разделителем
    is_admin = False
    try:
        if isinstance(ADMIN_ID, (list, tuple, set)):
            is_admin = int(user_id) in [int(x) for x in ADMIN_ID]
        else:
            is_admin = int(user_id) == int(ADMIN_ID)
    except Exception:
        is_admin = False

    if is_admin:
        builder.row(KeyboardButton(text="Сертификаты"))
        builder.row(KeyboardButton(text="Управление курсами и пользователями"))
    else:
        builder.row(KeyboardButton(text="Мои курсы"))
        builder.row(KeyboardButton(text="Мои сертификаты"))

    builder.row(KeyboardButton(text="Выход"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)
