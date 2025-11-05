import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from online_parser import OnlineNewsParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
news_parser = OnlineNewsParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти новости"), KeyboardButton(text="📰 Свежие ЭПР")],
        [KeyboardButton(text="⚡ Статус"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска актуальных новостей об ЭПР.\n\n"
        "🔍 Ищу в реальном времени в Google News и Яндекс.Новостях.\n\n"
        "Используйте кнопки ниже:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 Помощь:\n\n"
        "Кнопки:\n"
        "• 🔍 Найти новости - поиск по ключевым словам\n"
        "• 📰 Свежие ЭПР - последние новости\n"
        "• ⚡ Статус - проверка работы\n"
        "• ℹ️ Помощь - эта информация\n\n"
        "💡 Пишите любые запросы в чат!"
    )

@dp.message(lambda message: message.text == "🔍 Найти новости")
async def search_news(message: types.Message):
    await message.answer("🔍 Напишите ключевые слова для поиска:")

@dp.message(lambda message: message.text == "📰 Свежие ЭПР")
async def fresh_epr_news(message: types.Message):
    await message.answer("🔍 Ищу свежие новости об ЭПР...")
    
    try:
        news_items = await news_parser.search_news("ЭПР регуляторная песочница")
        
        if not news_items:
            await message.answer("📭 Свежих новостей не найдено.")
            return
        
        response = "📰 Свежие новости:\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"{i}. {item['title']}\n"
            response += f"🔗 {item['url']}\n"
            response += f"📌 {item['source']}\n"
            response += f"🕒 {item['date']}\n\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка при поиске.")

@dp.message(lambda message: message.text == "⚡ Статус")
async def check_status(message: types.Message):
    await message.answer("✅ Бот работает\n🔍 Парсер активен\n💡 Готов к поиску")

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_news(message)

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    await fresh_epr_news(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    if user_text.startswith('/') or user_text in ["🔍 Найти новости", "📰 Свежие ЭПР", "⚡ Статус", "ℹ️ Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу новости: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_news(user_text)
        
        if not news_items:
            await message.answer(f"📭 По '{user_text}' новостей не найдено.")
        else:
            response = f"🔍 Найдено по '{user_text}':\n\n"
            
            for i, item in enumerate(news_items, 1):
                response += f"{i}. {item['title']}\n"
                response += f"🔗 {item['url']}\n"
                response += f"📌 {item['source']}\n\n"
            
            await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка поиска.")

async def main():
    logger.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
