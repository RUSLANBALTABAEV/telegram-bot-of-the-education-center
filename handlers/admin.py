from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import Course, async_session
from fsm.courses import CourseFSM
from config.bot_config import ADMIN_ID

admin_router = Router()

# --- Добавление курса ---
@admin_router.message(Command("addcourse"))
async def start_add_course(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для добавления курсов.")
        return
    await message.answer("Введите название курса:")
    await state.set_state(CourseFSM.title)

@admin_router.message(CourseFSM.title)
async def process_course_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание курса:")
    await state.set_state(CourseFSM.description)

@admin_router.message(CourseFSM.description)
async def process_course_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену курса (число):")
    await state.set_state(CourseFSM.price)

@admin_router.message(CourseFSM.price, F.text.regexp(r"^\d+$"))
async def process_course_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    price = int(message.text)

    async with async_session() as session:
        new_course = Course(title=title, description=description, price=price)
        session.add(new_course)
        await session.commit()

    await message.answer(f"✅ Курс «{title}» добавлен!")
    await state.clear()

# --- Удаление курса ---
@admin_router.message(Command("delcourse"))
async def delete_course(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для удаления курсов.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Укажите название курса: /delcourse Python для начинающих")
        return

    title = args[1]
    async with async_session() as session:
        result = await session.execute(select(Course).where(Course.title == title))
        course = result.scalar_one_or_none()

        if not course:
            await message.answer("⚠️ Курс не найден.")
            return

        await session.delete(course)
        await session.commit()

    await message.answer(f"🗑 Курс «{title}» удалён!")

# --- Изменение цены курса ---
@admin_router.message(Command("editcourse"))
async def edit_course(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для изменения курсов.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Использование: /editcourse <Название> <Новая цена>")
        return

    title = args[1]
    new_price = int(args[2])

    async with async_session() as session:
        result = await session.execute(select(Course).where(Course.title == title))
        course = result.scalar_one_or_none()

        if not course:
            await message.answer("⚠️ Курс не найден.")
            return

        course.price = new_price
        await session.commit()

    await message.answer(f"✏️ Цена курса «{title}» изменена на {new_price} руб.")
