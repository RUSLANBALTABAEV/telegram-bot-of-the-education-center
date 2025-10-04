# ============ loader.py ============
"""
Модуль инициализации бота и диспетчера.
Содержит глобальные объекты Bot и Dispatcher для использования
в других модулях.
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.bot_config import API_TOKEN

# Инициализация бота с HTML parse mode по умолчанию
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

# Инициализация диспетчера с хранилищем в памяти
dp = Dispatcher(storage=MemoryStorage())
