from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import User
from db.session import async_session
from fsm.auth import Auth
from i18n.locales import get_text

auth_router = Router()

async def get_user_language(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"

@auth_router.message(Command("login"))
@auth_router.message(F.text.in_(["Авторизация", "Authorization", "Kirish"]))
async def start_auth(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if user and user.is_active:
        await message.answer(get_text("already_logged_in", lang))
    else:
        await message.answer(get_text("enter_phone_auth", lang))
        await state.set_state(Auth.phone)

@auth_router.message(Auth.phone, F.text.regexp(r"^\+?\d{10,15}$"))
async def process_phone_auth(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.phone == message.text)
        )
        user = result.scalar_one_or_none()

        if user:
            if user.user_id and user.is_active:
                await message.answer(get_text("account_already_active", lang))
            else:
                user.user_id = message.from_user.id
                user.is_active = True
                session.add(user)
                await session.commit()
                await message.answer(get_text("login_success", lang))
        else:
            await message.answer(get_text("user_not_found", lang))

    await state.clear()

@auth_router.message(Command("logout"))
@auth_router.message(F.text.in_(["Выход", "Logout", "Chiqish"]))
async def logout(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user and user.is_active:
            user.is_active = False
            session.add(user)
            await session.commit()
            await message.answer(get_text("logout_success", lang))
        else:
            await message.answer(get_text("not_authorized", lang))
