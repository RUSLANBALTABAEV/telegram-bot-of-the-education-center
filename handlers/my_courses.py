from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Certificate, Enrollment
from db.session import async_session
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from i18n.locales import get_text

my_courses_router = Router()

async def get_user_language(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"

@my_courses_router.message(Command("mycourses"))
@my_courses_router.message(F.text.in_(["Мои курсы", "My Courses", "Mening kurslarim"]))
async def show_my_courses(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        if not user:
            await message.answer(get_text("not_registered", lang))
            return

        result = await session.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.user_id == user.id)
        )
        enrollments = result.scalars().all()

    if not enrollments:
        await message.answer(get_text("no_my_courses", lang))
        return

    for enr in enrollments:
        course = enr.course
        
        if enr.is_completed:
            status = get_text("status_completed", lang)
        else:
            end_date_str = enr.end_date.strftime("%d.%m.%Y") if enr.end_date else get_text("not_indicated", lang)
            status = get_text("status_until", lang, date=end_date_str)
            
        text = (
            f"📘 <b>{course.title}</b>\n\n"
            f"{course.description or get_text('no_description', lang)}\n\n"
            f"{get_text('price', lang, price=course.price)}\n\n"
            f"{get_text('status', lang, status=status)}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text("btn_unenroll", lang), callback_data=f"unenroll:{course.id}")]
            ]
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
