from aiogram import Router, types
from aiogram.filters import Command
from keyboards.reply import main_menu

start_router = Router()


@start_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Добро пожаловать!\nВыберите действие:",
        reply_markup=main_menu(message.from_user.id)
    )
