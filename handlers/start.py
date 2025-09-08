from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.reply import main_menu

start_router = Router()


@start_router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    """
    await message.answer(
        "👋 Здравствуйте! Добро пожаловать!\nВыберите действие:",
        reply_markup=main_menu(message.from_user.id)
    )


@start_router.message(F.text == "Старт")
async def start_button_handler(message: types.Message):
    """
    Обработчик кнопки 'Старт'
    """
    await message.answer(
        "👋 Добро пожаловать! Выберите действие:",
        reply_markup=main_menu(message.from_user.id)
    )
