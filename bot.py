import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config.bot_config import API_TOKEN
from aiogram.types import FSInputFile, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

bot = Bot(API_TOKEN)
dp = Dispatcher()

TEXT = '''
/help - справочный текст
/start - запуск бота
'''

@dp.message(Command('start'))
async def start_command(message: types.Message):
    await message.answer('Привет, я бот!')


@dp.message(Command('help', prefix='$/'))
async def help_command(message: types.Message):
    await message.reply(TEXT)


async def main():

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
