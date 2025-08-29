import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config.bot_config import API_TOKEN
from keyboards.reply import main_menu  # импортируем клавиатуру

bot = Bot(API_TOKEN)
dp = Dispatcher()

TEXT = '''
/help - справочный информация
/start - запуск бота
'''

@dp.message(Command('start'))
async def start_command(message: types.Message):
    await message.answer(
        'Чтобы продолжить использовать бота, требуется…:',
        reply_markup=main_menu()
    )

@dp.message(Command('help', prefix='$/'))
async def help_command(message: types.Message):
    await message.reply(TEXT)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
