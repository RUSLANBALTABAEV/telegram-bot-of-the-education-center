# loader.py
from aiogram import Bot, Dispatcher
from config.bot_config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
