from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import User, async_session
from fsm.auth import Auth

auth_router = Router()

@auth_router.message(Command("login"))
@auth_router.message(F.text == "Авторизация")
async def start_auth(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == message.from_user.id))
        user = result.scalar_one_or_none()

    if user:
        await message.answer("✅ Вы уже вошли в систему!")
    else:
        await message.answer("Введите ваш номер телефона (в формате +79998887766):")
        await state.set_state(Auth.phone)


@auth_router.message(Auth.phone, F.text.regexp(r"^\+?\d{10,15}$"))
async def process_phone_auth(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == message.text))
        user = result.scalar_one_or_none()

        if user:
            if user.user_id:
                await message.answer("⚠️ Этот аккаунт уже привязан.")
            else:
                user.user_id = message.from_user.id
                session.add(user)
                await session.commit()
                await message.answer("✅ Вход выполнен!")
        else:
            await message.answer("⚠️ Пользователь не найден. Используйте /register.")

    await state.clear()


@auth_router.message(Command("logout"))
@auth_router.message(F.text == "Выход")
async def logout(message: types.Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user:
            user.user_id = None
            session.add(user)
            await session.commit()
            await message.answer("🚪 Вы вышли из системы.")
        else:
            await message.answer("⚠️ Вы не авторизованы.")
