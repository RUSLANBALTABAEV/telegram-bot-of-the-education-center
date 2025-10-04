# ============ handlers/courses.py ============
"""
Обработчики для просмотра курсов и записи на них.
"""
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import User, Course, Enrollment
from db.session import async_session
from i18n.locales import get_text

courses_router = Router()


async def get_user_language(user_id: int) -> str:
    """
    Получить язык пользователя из БД.

    Args:
        user_id: Telegram ID пользователя

    Returns:
        Код языка (ru/en/uz), по умолчанию 'ru'
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"


async def build_courses_message(
    lang: str = "ru"
) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Построить сообщение со списком курсов.

    Args:
        lang: Код языка интерфейса

    Returns:
        Кортеж (текст сообщения, клавиатура)
    """
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        return get_text("no_courses", lang), None

    text = get_text("available_courses", lang)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=course.title,
                    callback_data=f"course:{course.id}"
                )
            ]
            for course in courses
        ]
    )
    return text, keyboard


@courses_router.message(Command("courses"))
@courses_router.message(F.text.in_(["Курсы", "Courses", "Kurslar"]))
async def show_courses(message: Message) -> None:
    """
    Показать список доступных курсов.

    Args:
        message: Входящее сообщение
    """
    lang = await get_user_language(message.from_user.id)
    text, keyboard = await build_courses_message(lang)

    if not keyboard:
        await message.answer(text)
    else:
        await message.answer(text, reply_markup=keyboard)


@courses_router.callback_query(F.data.startswith("course:"))
async def show_course_info(callback: CallbackQuery) -> None:
    """
    Показать информацию о конкретном курсе.

    Args:
        callback: Callback query с ID курса
    """
    lang = await get_user_language(callback.from_user.id)
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer(
                get_text("course_not_found", lang),
                show_alert=True
            )
            return

        # Проверка пользователя
        result_user = await session.execute(
            select(User).where(User.user_id == callback.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        enrollment = None
        if user:
            result = await session.execute(
                select(Enrollment)
                .options(selectinload(Enrollment.course))
                .where(
                    Enrollment.user_id == user.id,
                    Enrollment.course_id == course_id
                )
            )
            enrollment = result.scalar_one_or_none()

    # Формируем текст курса
    start_date_str = (
        course.start_date.strftime("%d.%m.%Y")
        if course.start_date
        else get_text("not_indicated", lang)
    )
    end_date_str = (
        course.end_date.strftime("%d.%m.%Y")
        if course.end_date
        else get_text("not_indicated", lang)
    )

    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description}\n\n"
        f"{get_text('price', lang, price=course.price)}\n"
        f"{get_text('dates', lang, start=start_date_str, end=end_date_str)}"
    )

    # Кнопки
    if enrollment:
        if enrollment.is_completed:
            status = get_text("status_completed", lang)
        else:
            end_date_display = (
                enrollment.end_date.strftime("%d.%m.%Y")
                if enrollment.end_date
                else get_text("not_indicated", lang)
            )
            status = get_text("status_until", lang, date=end_date_display)

        text += f"\n\n{get_text('status', lang, status=status)}"
        action_button = InlineKeyboardButton(
            text=get_text("btn_unenroll", lang),
            callback_data=f"unenroll:{course.id}"
        )
    else:
        action_button = InlineKeyboardButton(
            text=get_text("btn_enroll", lang),
            callback_data=f"enroll:{course.id}"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [action_button],
            [
                InlineKeyboardButton(
                    text=get_text("btn_back", lang),
                    callback_data="back_to_courses"
                )
            ]
        ]
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@courses_router.callback_query(F.data.startswith("enroll:"))
async def enroll_course(callback: CallbackQuery) -> None:
    """
    Записать пользователя на курс.

    Args:
        callback: Callback query с ID курса
    """
    lang = await get_user_language(callback.from_user.id)
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        # Проверка пользователя
        result = await session.execute(
            select(User).where(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer(
                get_text("register_first", lang),
                show_alert=True
            )
            return

        # Проверка курса
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer(
                get_text("course_not_found", lang),
                show_alert=True
            )
            return

        # Проверка записи
        existing = await session.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id,
                Enrollment.course_id == course_id
            )
        )
        if existing.scalar_one_or_none():
            await callback.answer(
                get_text("already_enrolled", lang),
                show_alert=True
            )
            return

        # Создаём запись с датами из курса
        enrollment = Enrollment(
            user_id=user.id,
            course_id=course.id,
            start_date=course.start_date or date.today(),
            end_date=course.end_date,
            is_completed=False
        )
        session.add(enrollment)
        await session.commit()

    await callback.message.edit_text(
        get_text("enrolled_success", lang, title=course.title)
    )


@courses_router.callback_query(F.data.startswith("unenroll:"))
async def unenroll_course(callback: CallbackQuery) -> None:
    """
    Отписать пользователя от курса.

    Args:
        callback: Callback query с ID курса
    """
    lang = await get_user_language(callback.from_user.id)
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer(
                get_text("register_first", lang),
                show_alert=True
            )
            return

        enrollment_q = await session.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id,
                Enrollment.course_id == course_id
            )
        )
        enrollment = enrollment_q.scalar_one_or_none()

        if not enrollment:
            await callback.answer(
                get_text("not_enrolled", lang),
                show_alert=True
            )
            return

        await session.delete(enrollment)
        await session.commit()

    await callback.message.edit_text(get_text("unenrolled_success", lang))


@courses_router.callback_query(F.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery) -> None:
    """
    Вернуться к списку курсов.

    Args:
        callback: Callback query
    """
    lang = await get_user_language(callback.from_user.id)
    text, keyboard = await build_courses_message(lang)

    if not keyboard:
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)

    await callback.answer()
