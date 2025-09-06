from aiogram import Router, F, types
from sqlalchemy import select
from db.models import Certificate, User
from db.session import async_session
from config.bot_config import ADMIN_ID
from keyboards.reply import main_menu

certificates_router = Router()


@certificates_router.message(F.text == "Сертификаты")
async def show_all_certificates(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    async with async_session() as session:
        result = await session.execute(select(Certificate))
        certificates = result.scalars().all()

        if not certificates:
            await message.answer("📭 Сертификатов пока нет.", reply_markup=main_menu(message.from_user.id))
            return

        for cert in certificates:
            user = await session.get(User, cert.user_id)
            text = f"🏅 {cert.title}\n👤 Пользователь: {user.name if user else cert.user_id}"
            await message.answer(text)

            if cert.file_id:
                try:
                    await message.answer_document(cert.file_id, caption="📄 Файл сертификата")
                except Exception:
                    await message.answer("⚠️ Ошибка при отправке файла сертификата.")

    await message.answer("🔙 Главное меню", reply_markup=main_menu(message.from_user.id))


@certificates_router.message(F.text == "Мои сертификаты")
async def show_my_certificates(message: types.Message):
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        if not user:
            await message.answer(
                "⚠️ Вы не зарегистрированы. Используйте /register.",
                reply_markup=main_menu(message.from_user.id)
            )
            return

        result = await session.execute(
            select(Certificate).where(Certificate.user_id == user.id)
        )
        certificates = result.scalars().all()

    if not certificates:
        await message.answer("📭 У вас пока нет сертификатов.", reply_markup=main_menu(message.from_user.id))
        return

    for cert in certificates:
        await message.answer(f"🏅 {cert.title}")

        if cert.file_id:
            try:
                await message.answer_document(cert.file_id, caption="📄 Ваш сертификат")
            except Exception:
                await message.answer("⚠️ Ошибка при отправке сертификата.")

    await message.answer("🔙 Главное меню", reply_markup=main_menu(message.from_user.id))
