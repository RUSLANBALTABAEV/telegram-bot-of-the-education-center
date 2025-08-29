from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Регистрация'))
    builder.row(KeyboardButton(text='Авторизация'))
    return builder.as_markup(resize_keyboard=True)
