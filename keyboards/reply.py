from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config.bot_config import ADMIN_ID

def main_menu(user_id: int):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Регистрация"))
    builder.row(KeyboardButton(text="Авторизация"))
    builder.row(KeyboardButton(text="Курсы"))
    builder.row(KeyboardButton(text="Мои курсы"))

    if int(user_id) == int(ADMIN_ID):
        builder.row(KeyboardButton(text="Сертификаты"))  # ✅ для админа
        builder.row(KeyboardButton(text="Управление курсами и пользователями"))
    else:
        builder.row(KeyboardButton(text="Мои сертификаты"))  # ✅ для пользователя

    builder.row(KeyboardButton(text="Выход"))
    return builder.as_markup(resize_keyboard=True)
