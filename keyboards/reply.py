# keyboards/reply.py
from aiogram.types import KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config.bot_config import ADMIN_ID
from i18n.locales import get_text, AVAILABLE_LANGUAGES

def main_menu(user_id: int, lang: str = "ru"):
    """
    Возвращает клавиатуру — для админа и для обычного пользователя.
    """
    builder = ReplyKeyboardBuilder()

    # добавляем кнопку "Старт" в начало
    builder.row(KeyboardButton(text=get_text("btn_start", lang)))

    # основные кнопки для всех
    builder.row(KeyboardButton(text=get_text("btn_registration", lang)))
    builder.row(KeyboardButton(text=get_text("btn_auth", lang)))
    builder.row(KeyboardButton(text=get_text("btn_courses", lang)))

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
        builder.row(KeyboardButton(text=get_text("btn_admin_certificates", lang)))
        builder.row(KeyboardButton(text=get_text("btn_admin_panel", lang)))
    else:
        builder.row(KeyboardButton(text=get_text("btn_my_courses", lang)))
        builder.row(KeyboardButton(text=get_text("btn_certificates", lang)))

    builder.row(KeyboardButton(text=get_text("btn_language", lang)))
    builder.row(KeyboardButton(text=get_text("btn_logout", lang)))
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)

def language_keyboard():
    """
    Клавиатура для выбора языка
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
            for code, name in AVAILABLE_LANGUAGES.items()
        ]
    )
    return keyboard

def admin_main_keyboard(lang: str = "ru"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_show_users", lang), callback_data="show_users")],
            [InlineKeyboardButton(text=get_text("btn_manage_courses", lang), callback_data="manage_courses")],
            [InlineKeyboardButton(text=get_text("btn_add_course", lang), callback_data="add_course")],
            [InlineKeyboardButton(text=get_text("btn_add_certificate", lang), callback_data="add_certificate")],
            [InlineKeyboardButton(text=get_text("btn_delete_all_users", lang), callback_data="delete_all_users")],
        ]
    )

def admin_back_keyboard(lang: str = "ru"):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=get_text("btn_admin_back", lang), callback_data="admin_menu")]]
    )
