import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from smart_parser import SmartNewsParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
news_parser = SmartNewsParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск новостей"), KeyboardButton(text="📰 Актуальные ЭПР")],
        [KeyboardButton(text="🌐 Источники"), KeyboardButton(text="💡 Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска новостей об ЭПР и регуляторных песочницах.\n\n"
        "🔍 **Я использую:**\n"
        "• Умный поиск по разным источникам\n"
        "• Альтернативные методы доступа\n"
        "• Актуальные данные\n\n"
        "💡 **Работает даже при проблемах с сетью!**",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Помощь по боту:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search - поиск новостей\n"
        "/news - актуальные ЭПР\n"
        "/help - помощь\n\n"
        "**Кнопки:**\n"
        "• 🔍 Поиск новостей - найти по ключевым словам\n"
        "• 📰 Актуальные ЭПР - свежие материалы\n"
        "• 🌐 Источники - информация о поиске\n"
        "• 💡 Помощь - эта информация\n\n"
        "💡 Просто напишите любой запрос в чат!"
    )

@dp.message(lambda message: message.text == "🔍 Поиск новостей")
async def search_news(message: types.Message):
    await message.answer(
        "🔍 **Умный поиск новостей**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры запросов:\n"
        "• `песочница регуляторная`\n"
        "• `ЭПР новости`\n"
        "• `экспериментальный правовой режим`\n"
        "• `цифровая песочница`\n\n"
        "⚡ Использую продвинутые методы поиска!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "📰 Актуальные ЭПР")
async def fresh_epr_news(message: types.Message):
    await message.answer("🔍 Ищу актуальную информацию об ЭПР...")
    
    try:
        news_items = await news_parser.search_news("ЭПР регуляторная песочница экспериментальный правовой режим")
        
        response = "📰 **Актуальная информация об ЭПР:**\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Открыть]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"📅 {item['date']}\n\n"
        
        response += "💡 *Информация обновляется в реальном времени*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Временная ошибка. Попробуйте другой запрос.")

@dp.message(lambda message: message.text == "🌐 Источники")
async def show_sources(message: types.Message):
    await message.answer(
        "🌐 **Методы поиска:**\n\n"
        "🔍 **Основные источники:**\n"
        "• DuckDuckGo Search API\n"
        "• Bing News RSS\n"
        "• NewsAPI публичные данные\n"
        "• Официальные сайты\n\n"
        "⚡ **Особенности:**\n"
        "• Работает при блокировках\n"
        "• Использует альтернативные методы\n"
        "• Всегда возвращает актуальные ссылки\n\n"
        "💡 Бот находит реальные источники информации!"
    )

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_news(message)

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    await fresh_epr_news(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    if user_text.startswith('/') or user_text in ["🔍 Поиск новостей", "📰 Актуальные ЭПР", "🌐 Источники", "💡 Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу информацию по запросу: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_news(user_text)
        
        response = f"🔍 **Результаты по '{user_text}':**\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Открыть]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            if len(news_items) <= 3:  # Показываем описание только если мало результатов
                response += f"📝 {item['description']}\n"
            response += f"📅 {item['date']}\n\n"
        
        response += "💡 *Все ссылки ведут на актуальные источники*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(
            f"❌ Ошибка при поиске по '{user_text}'.\n\n"
            "💡 **Попробуйте:**\n"
            "• Другие ключевые слова\n"
            "• Более короткий запрос\n"
            "• Проверить интернет-соединение"
        )

async def main():
    logger.info("Умный бот запускается...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка вебхука: {e}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
