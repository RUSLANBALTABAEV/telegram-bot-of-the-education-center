from config.bot_config import SQLALCHEMY_URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Создаём движок
engine = create_async_engine(SQLALCHEMY_URL, echo=True)

# Создаём фабрику сессий
async_session = async_sessionmaker(engine, expire_on_commit=False)
