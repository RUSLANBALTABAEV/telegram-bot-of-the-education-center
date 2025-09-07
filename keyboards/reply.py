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

    # основные кнопки для всех
    builder.row(KeyboardButton(text="Регистрация"))
    builder.row(KeyboardButton(text="Авторизация"))
    builder.row(KeyboardButton(text="Курсы"))

    # безопасная проверка — ADMIN_ID может быть int или список/кортеж/строка с разделителем
    is_admin = False
    try:
        # если в config положили список/кортеж/сет
        if isinstance(ADMIN_ID, (list, tuple, set)):
            is_admin = int(user_id) in [int(x) for x in ADMIN_ID]
        else:
            # обычно ADMIN_ID — int
            is_admin = int(user_id) == int(ADMIN_ID)
    except Exception:
        is_admin = False

    if is_admin:
        # Точные тексты — такие же, что и в handlers/certificates.py и handlers/admin.py
        builder.row(KeyboardButton(text="Сертификаты"))
        builder.row(KeyboardButton(text="Управление курсами и пользователями"))
    else:
        # Точные тексты — такие же, что и в handlers/my_courses.py и handlers/certificates.py
        builder.row(KeyboardButton(text="Мои курсы"))
        builder.row(KeyboardButton(text="Мои сертификаты"))

    builder.row(KeyboardButton(text="Выход"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)
