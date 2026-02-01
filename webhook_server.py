# ============ webhook_server.py ============
"""
FastAPI сервер для обработки webhook от Telegram через Cloudflare
Полностью интегрирован с вашим aiogram ботом
"""
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
from typing import Optional

from loader import bot, dp
from handlers.registration import registration_router
from handlers.auth import auth_router
from handlers.start import start_router
from handlers.courses import courses_router
from handlers.admin import admin_router
from handlers.my_courses import my_courses_router
from handlers.certificates import certificates_router
from notifier import setup_scheduler
from db.models import create_db, seed_courses
from db.session import engine
from config.bot_config import API_TOKEN

# ============ Настройка логирования ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация при запуске и очистка при выключении
    """
    # ============ STARTUP ============
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК WEBHOOK СЕРВЕРА")
    logger.info("=" * 50)
    
    try:
        # Создаём таблицы в БД
        logger.info("📦 Создание таблиц в БД...")
        await create_db(engine)
        logger.info("✅ Таблицы БД созданы")
        
        # Добавляем курсы по умолчанию
        logger.info("📚 Инициализация курсов...")
        await seed_courses()
        logger.info("✅ Курсы инициализированы")
        
        # Регистрируем роутеры
        logger.info("🔌 Регистрация роутеров...")
        dp.include_router(start_router)
        dp.include_router(registration_router)
        dp.include_router(auth_router)
        dp.include_router(courses_router)
        dp.include_router(my_courses_router)
        dp.include_router(admin_router)
        dp.include_router(certificates_router)
        logger.info("✅ Роутеры зарегистрированы")
        
        # Запускаем планировщик уведомлений
        logger.info("⏰ Запуск планировщика уведомлений...")
        setup_scheduler()
        logger.info("✅ Планировщик уведомлений запущен")
        
        # Получаем информацию о боте
        try:
            me = await bot.get_me()
            logger.info(f"🤖 Bot: @{me.username} (ID: {me.id})")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении информации о боте: {e}")
        
        logger.info("=" * 50)
        logger.info("✅ ВСЕ КОМПОНЕНТЫ УСПЕШНО ИНИЦИАЛИЗИРОВАНЫ")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ИНИЦИАЛИЗАЦИИ: {e}")
        raise
    
    yield
    
    # ============ SHUTDOWN ============
    logger.info("🛑 Выключение сервера...")
    try:
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при закрытии сессии: {e}")


app = FastAPI(
    title="Education Bot Webhook Server",
    description="FastAPI сервер для обработки webhook от Telegram",
    version="1.0.0",
    lifespan=lifespan
)


# ============ HEALTH CHECK ============
@app.get("/health")
async def health_check():
    """
    Проверка здоровья сервиса
    
    Returns:
        JSON с информацией о состоянии
    """
    try:
        # Проверяем подключение к БД
        from sqlalchemy import text
        from db.session import async_session
        
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        
        logger.info("✅ Health check прошёл успешно")
        return JSONResponse({
            "status": "healthy",
            "bot": "running",
            "database": "connected",
            "message": "Все системы работают корректно"
        }, status_code=200)
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "message": "Проблема с подключением к БД"
        }, status_code=503)


# ============ WEBHOOK HANDLER ============
@app.post("/webhook")
async def webhook_handler(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Основной обработчик webhook от Telegram
    
    Args:
        request: HTTP запрос от Telegram
        x_telegram_bot_api_secret_token: Secret token для проверки подлинности
    
    Returns:
        JSON ответ
    """
    try:
        # Проверяем secret token для безопасности
        if x_telegram_bot_api_secret_token != API_TOKEN:
            logger.warning(
                f"⚠️ Попытка доступа с неверным токеном: "
                f"{x_telegram_bot_api_secret_token}"
            )
            return JSONResponse(
                {"ok": False, "error": "Invalid token"},
                status_code=401
            )
        
        # Получаем update от Telegram
        update_data = await request.json()
        update_id = update_data.get('update_id')
        
        # Логируем входящий update
        if 'message' in update_data:
            msg = update_data['message']
            logger.info(
                f"📨 Update #{update_id}: Message от "
                f"{msg.get('from', {}).get('first_name')} "
                f"(ID: {msg.get('from', {}).get('id')})"
            )
        elif 'callback_query' in update_data:
            cb = update_data['callback_query']
            logger.info(
                f"📨 Update #{update_id}: Callback от "
                f"{cb.get('from', {}).get('first_name')} "
                f"(Data: {cb.get('data')})"
            )
        else:
            logger.info(f"📨 Update #{update_id}: {list(update_data.keys())}")
        
        # Обрабатываем update через диспетчер
        await dp.feed_update(bot, update_data)
        
        logger.debug(f"✅ Update #{update_id} успешно обработан")
        return JSONResponse({"ok": True}, status_code=200)
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )


# ============ WEBHOOK INFO ============
@app.get("/webhook-info")
async def webhook_info():
    """
    Получить информацию о текущем webhook
    
    Returns:
        JSON с информацией о webhook
    """
    try:
        info = await bot.get_webhook_info()
        logger.info(f"📋 Запрос информации о webhook")
        
        return JSONResponse({
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "allowed_updates": info.allowed_updates,
        }, status_code=200)
    except Exception as e:
        logger.error(f"❌ Ошибка при получении информации о webhook: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


# ============ WEBHOOK SETUP ============
@app.post("/webhook-set")
async def webhook_set(webhook_url: str):
    """
    Установить webhook на новый URL
    
    Usage: 
        curl -X POST "http://localhost:8000/webhook-set?webhook_url=https://yourdomain.com/webhook"
    
    Args:
        webhook_url: URL для webhook
    
    Returns:
        JSON ответ
    """
    try:
        logger.info(f"🔧 Попытка установки webhook: {webhook_url}")
        
        # Удаляем старый webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🗑️ Старый webhook удалён")
        
        # Устанавливаем новый
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "inline_query"],
            secret_token=API_TOKEN
        )
        logger.info(f"✅ Webhook установлен: {webhook_url}")
        
        return JSONResponse({
            "ok": True,
            "message": f"Webhook установлен: {webhook_url}"
        }, status_code=200)
    except Exception as e:
        logger.error(f"❌ Ошибка при установке webhook: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )


# ============ WEBHOOK DELETE ============
@app.post("/webhook-delete")
async def webhook_delete():
    """
    Удалить webhook
    
    Returns:
        JSON ответ
    """
    try:
        logger.info("🗑️ Попытка удаления webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook успешно удалён")
        
        return JSONResponse({
            "ok": True,
            "message": "Webhook успешно удалён"
        }, status_code=200)
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении webhook: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )


# ============ ROOT ENDPOINT ============
@app.get("/")
async def root():
    """
    Главная страница с информацией об API
    
    Returns:
        JSON с информацией об эндпоинтах
    """
    return JSONResponse({
        "name": "Education Bot Webhook Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "GET /": "Информация об API",
            "GET /health": "Проверка здоровья сервиса",
            "POST /webhook": "Основной обработчик webhook (от Telegram)",
            "GET /webhook-info": "Информация о текущем webhook",
            "POST /webhook-set": "Установить webhook на новый URL",
            "POST /webhook-delete": "Удалить webhook",
            "GET /docs": "Swagger документация",
            "GET /redoc": "ReDoc документация"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    })


# ============ STARTUP MESSAGE ============
@app.get("/startup-info")
async def startup_info():
    """
    Информация о готовности сервера к работе
    """
    try:
        # Проверяем БД
        from sqlalchemy import text
        from db.session import async_session
        
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        
        # Получаем информацию о боте
        me = await bot.get_me()
        
        # Получаем информацию о webhook
        webhook_info = await bot.get_webhook_info()
        
        return JSONResponse({
            "status": "ready",
            "bot": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "is_bot": me.is_bot
            },
            "webhook": {
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count,
            },
            "database": "connected",
            "scheduler": "running"
        }, status_code=200)
    except Exception as e:
        logger.error(f"❌ Ошибка при получении информации о статусе: {e}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
