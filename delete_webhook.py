import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

async def delete_webhook():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    try:
        await bot.delete_webhook()
        print("✅ Вебхук успешно удален!")
        print("Теперь можно запустить бота в режиме polling")
    except Exception as e:
        print(f"❌ Ошибка при удалении вебхука: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(delete_webhook())
