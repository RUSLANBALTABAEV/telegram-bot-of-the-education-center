from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import Course, User, async_session
from fsm.courses import CourseFSM
from config.bot_config import ADMIN_ID

admin_router = Router()

# --- Добавление курса ---
@admin_router.message(Command("addcourse"))
@admin_router.message(F.text == "Добавить курс")
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

# --- Просмотр пользователей ---
@admin_router.message(Command("users"))
@admin_router.message(F.text == "Пользователи")
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).options(selectinload(User.courses)))
        users = result.scalars().all()

    if not users:
        await message.answer("📭 Пользователей пока нет.")
        return

    for user in users:
        text = (
            f"👤 <b>{user.name}</b>\n"
            f"📱 {user.phone}\n"
            f"🎂 {user.age} лет\n"
        )
        if user.courses:
            text += "📚 Курсы: " + ", ".join([c.title for c in user.courses])

        if user.photo:
            await message.answer_photo(user.photo, caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

        if user.document:
            await message.answer_document(user.document, caption="📄 Документ")
