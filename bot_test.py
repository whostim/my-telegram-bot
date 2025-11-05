import os
import logging
from dotenv import load_dotenv

# Проверка базовой функциональности
def test_environment():
    load_dotenv()
    token = os.getenv('BOT_TOKEN')
    
    if token and token != "your_bot_token_here":
        print("✅ .env файл настроен правильно")
        print(f"Токен: {token[:10]}...")
    else:
        print("❌ Необходимо настроить .env файл с BOT_TOKEN")
    
    # Проверяем установленные пакеты
    try:
        from aiogram import Bot, Dispatcher
        print("✅ Aiogram установлен")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")

if __name__ == "__main__":
    test_environment()
