import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from real_parser import RealNewsParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
news_parser = RealNewsParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📰 Реальные новости"), KeyboardButton(text="🔍 Поиск")],
        [KeyboardButton(text="🛠️ Статус"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска реальных новостей.\n\n"
        "🔍 **Что я делаю:**\n"
        "• Ищу в Google News\n"
        "• Ищу в Яндекс.Новостях\n"
        "• Проверяю RSS ленты\n\n"
        "⚡ **Статус:** Реальный поиск активен!",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "📰 Реальные новости")
async def real_news(message: types.Message):
    await message.answer("🔍 Ищу реальные новости о регуляторных песочницах...")
    
    try:
        news_items = await news_parser.search_news("регуляторная песочница")
        
        if not news_items:
            await message.answer(
                "📭 Реальных новостей не найдено.\n\n"
                "💡 **Возможные причины:**\n"
                "• Сейчас нет свежих новостей по теме\n"
                "• Проблемы с доступом к источникам\n"
                "• Попробуйте другие ключевые слова"
            )
            return
        
        response = "📰 **Реальные новости:**\n\n"
        
        for i, item in enumerate(news_items[:5], 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            if item.get('description'):
                response += f"📝 {item['description'][:100]}...\n"
            response += f"📅 {item.get('date', 'Не указано')}\n\n"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer("❌ Ошибка при поиске реальных новостей. Попробуйте позже.")

@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_menu(message: types.Message):
    await message.answer(
        "🔍 **Реальный поиск**\n\n"
        "Напишите ключевые слова для поиска в реальных источниках:\n\n"
        "Примеры:\n"
        "• `песочница`\n"
        "• `ЭПР`\n"
        "• `регуляторный`\n"
        "• `правовой эксперимент`"
    )

@dp.message(lambda message: message.text == "🛠️ Статус")
async def status_check(message: types.Message):
    await message.answer(
        "🛠️ **Статус системы:**\n\n"
        "✅ Бот активен\n"
        "✅ Парсер запущен\n"
        "🔍 Источники:\n"
        "• Google News\n"
        "• Яндекс.Новости\n"
        "• RSS ленты\n\n"
        "💡 Поиск работает в реальном времени!"
    )

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    if user_text.startswith('/') or user_text in ["📰 Реальные новости", "🔍 Поиск", "🛠️ Статус", "ℹ️ Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу реальные новости по запросу: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_news(user_text)
        
        if not news_items:
            await message.answer(
                f"🔍 По запросу '{user_text}' не найдено реальных новостей.\n\n"
                "💡 **Попробуйте:**\n"
                "• Другие ключевые слова\n"
                "• Более общий запрос\n"
                "• Поискать позже"
            )
        else:
            response = f"🔍 **Реальные новости по '{user_text}':**\n\n"
            
            for i, item in enumerate(news_items[:5], 1):
                response += f"**{i}. {item['title']}**\n"
                response += f"🔗 [Читать]({item['url']})\n"
                response += f"📌 {item['source']}\n\n"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer("❌ Ошибка при поиске. Проверьте подключение к интернету.")

async def main():
    logger.info("Гибридный бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
