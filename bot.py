import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from api_token import TOKEN

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= FSM ===================
class RegisterForm(StatesGroup):
    fio = State()
    phone = State()

class AuthForm(StatesGroup):
    fio = State()
    phone = State()

# ================= Команды ===================
@dp.message(Command("start"))
async def start_command(message: types.Message):
    kb = [
        [KeyboardButton(text="Регистрация"), KeyboardButton(text="Авторизация")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Здравствуйте! Это бот учебного центра.\nВыберите действие:", reply_markup=keyboard)

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.reply("/start - запуск бота\n/help - помощь")

# ================= Регистрация ===================
@dp.message(F.text == "Регистрация")
async def registration_start(message: types.Message, state: FSMContext):
    await message.answer("Введите ФИО (Имя Фамилия Отчество):")
    await state.set_state(RegisterForm.fio)

@dp.message(RegisterForm.fio)
async def process_fio_reg(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer("Введите номер телефона:")
    await state.set_state(RegisterForm.phone)

@dp.message(RegisterForm.phone)
async def process_phone_reg(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    kb = [[KeyboardButton(text="Назад")]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        f"Регистрация завершена ✅\n\nФИО: {data['fio']}\nТелефон: {data['phone']}\n\nТеперь авторизуйтесь.",
        reply_markup=keyboard
    )
    await state.clear()

# ================= Авторизация ===================
@dp.message(F.text == "Авторизация")
async def auth_start(message: types.Message, state: FSMContext):
    await message.answer("Введите ФИО:")
    await state.set_state(AuthForm.fio)

@dp.message(AuthForm.fio)
async def process_fio_auth(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer("Введите телефон:")
    await state.set_state(AuthForm.phone)

@dp.message(AuthForm.phone)
async def process_phone_auth(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    kb = [
        [KeyboardButton(text="Запись на курсы"), KeyboardButton(text="Расписание")],
        [KeyboardButton(text="Назад")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        f"Авторизация успешна ✅\nДобро пожаловать, {data['fio']}!",
        reply_markup=keyboard
    )
    await state.clear()

# ================= Запись на курсы ===================
@dp.message(F.text == "Запись на курсы")
async def show_courses(message: types.Message):
    courses = [
        "Python — 15 000₽",
        "Frontend — 18 000₽",
        "Data Science — 25 000₽"
    ]
    kb = [[KeyboardButton(text=f"Записаться: {c}")] for c in courses]
    kb.append([KeyboardButton(text="Назад")])
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer("Доступные курсы:\n" + "\n".join(courses), reply_markup=keyboard)

@dp.message(F.text.startswith("Записаться:"))
async def enroll_course(message: types.Message):
    course = message.text.replace("Записаться: ", "")
    await message.answer(f"Вы успешно записаны на курс: {course} ✅")

# ================= Расписание ===================
@dp.message(F.text == "Расписание")
async def show_schedule(message: types.Message):
    await message.answer("Расписание занятий:\n\nПн, Ср, Пт — 18:00\nСб — 12:00")

# ================= Кнопка назад ===================
@dp.message(F.text == "Назад")
async def back_button(message: types.Message):
    kb = [
        [KeyboardButton(text="Регистрация"), KeyboardButton(text="Авторизация")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Главное меню:", reply_markup=keyboard)

# ================= Запуск ===================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
