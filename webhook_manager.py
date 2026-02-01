#!/usr/bin/env python3
"""
Утилита для управления webhook'ом Telegram бота
"""
import asyncio
import sys
from pathlib import Path

# Добавляем текущую папку в path
sys.path.insert(0, str(Path(__file__).parent))

from loader import bot
from config.bot_config import API_TOKEN


async def set_webhook(webhook_url: str, secret_token: str = None):
    """Установить webhook"""
    print(f"🔧 Установка webhook: {webhook_url}")
    
    try:
        # Удаляем старый webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("🗑️  Старый webhook удалён")
        
        # Устанавливаем новый
        result = await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "inline_query"],
            secret_token=secret_token or API_TOKEN
        )
        
        if result:
            print(f"✅ Webhook успешно установлен!")
            print(f"📍 URL: {webhook_url}")
            return True
        else:
            print("❌ Не удалось установить webhook")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def get_webhook_info():
    """Получить информацию о webhook"""
    print("📋 Информация о webhook:")
    print("-" * 50)
    
    try:
        info = await bot.get_webhook_info()
        
        print(f"URL:                    {info.url}")
        print(f"Custom certificate:     {info.has_custom_certificate}")
        print(f"Pending updates:        {info.pending_update_count}")
        print(f"Last error date:        {info.last_error_date}")
        print(f"Last error message:     {info.last_error_message}")
        print(f"Max connections:        {info.max_connections}")
        print(f"Allowed updates:        {info.allowed_updates}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def delete_webhook():
    """Удалить webhook"""
    print("🗑️  Удаление webhook...")
    
    try:
        result = await bot.delete_webhook(drop_pending_updates=True)
        
        if result:
            print("✅ Webhook успешно удалён!")
            return True
        else:
            print("❌ Не удалось удалить webhook")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def get_bot_info():
    """Получить информацию о боте"""
    print("🤖 Информация о боте:")
    print("-" * 50)
    
    try:
        me = await bot.get_me()
        
        print(f"ID:                 {me.id}")
        print(f"Username:           @{me.username}")
        print(f"First name:         {me.first_name}")
        print(f"Is bot:             {me.is_bot}")
        print(f"Can join groups:    {me.can_join_groups}")
        print(f"Can read all group messages: {me.can_read_all_group_messages}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


async def main():
    """Главная функция"""
    print("=" * 50)
    print("🤖 TELEGRAM BOT WEBHOOK MANAGER")
    print("=" * 50)
    print()
    
    if len(sys.argv) < 2:
        print("📖 Использование:")
        print()
        print("  python webhook_manager.py set <url>")
        print("    Установить webhook на URL")
        print()
        print("  python webhook_manager.py info")
        print("    Получить информацию о webhook")
        print()
        print("  python webhook_manager.py delete")
        print("    Удалить webhook")
        print()
        print("  python webhook_manager.py bot-info")
        print("    Получить информацию о боте")
        print()
        print("📝 Примеры:")
        print()
        print("  python webhook_manager.py set https://api.yourdomain.com/webhook")
        print("  python webhook_manager.py info")
        print("  python webhook_manager.py delete")
        print()
        return
    
    command = sys.argv[1].lower()
    
    if command == "set":
        if len(sys.argv) < 3:
            print("❌ Укажите URL webhook'а")
            print("   Пример: python webhook_manager.py set https://api.yourdomain.com/webhook")
            return
        
        webhook_url = sys.argv[2]
        success = await set_webhook(webhook_url)
        
        if success:
            print()
            await get_webhook_info()
    
    elif command == "info":
        await get_webhook_info()
    
    elif command == "delete":
        success = await delete_webhook()
        
        if success:
            print()
            await get_webhook_info()
    
    elif command == "bot-info":
        await get_bot_info()
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        print()
        print("Доступные команды: set, info, delete, bot-info")


if __name__ == "__main__":
    asyncio.run(main())
