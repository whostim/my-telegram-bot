import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from advanced_online_parser import AdvancedOnlineParser

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
news_parser = AdvancedOnlineParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск новостей"), KeyboardButton(text="📈 Тренды ЭПР")],
        [KeyboardButton(text="🆘 Помощь"), KeyboardButton(text="🔄 Обновить")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска актуальных новостей об экспериментально-правовых режимах (ЭПР) в РФ.\n\n"
        "⚡ **Я ищу в реальном времени:**\n"
        "• Google News (русскоязычные источники)\n"
        "• Яндекс.Новости\n"
        "• Международные источники (Reddit, BBC)\n"
        "• RSS ленты\n\n"
        "🔍 **Чем новее новость, тем выше в результатах!**\n\n"
        "💡 Используйте кнопки ниже для работы:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🆘 **Помощь по боту:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search <запрос> - поиск новостей\n"
        "/trends - трендовые новости по ЭПР\n"
        "/help - помощь\n\n"
        "**Кнопки:**\n"
        "• 🔍 Поиск новостей - найти по ключевым словам\n"
        "• 📈 Тренды ЭПР - самые свежие новости по теме\n"
        "• 🆘 Помощь - эта информация\n"
        "• 🔄 Обновить - обновить результаты\n\n"
        "💡 **Примеры запросов:**\n"
        "• `песочница регуляторная`\n"
        "• `ЭПР Россия`\n"
        "• `экспериментальный правовой режим`\n"
        "• `цифровая песочница`\n\n"
        "⚡ Бот ищет только самые свежие новости (за последние 7 дней)!"
    )

@dp.message(lambda message: message.text == "🔍 Поиск новостей")
async def search_news(message: types.Message):
    await message.answer(
        "🔍 **Поиск актуальных новостей**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры:\n"
        "• `песочница регуляторная`\n"
        "• `ЭПР`\n"
        "• `правовой эксперимент`\n"
        "• `цифровая песочница Москва`\n\n"
        "⚡ Ищу в реальном времени по всем источникам!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "📈 Тренды ЭПР")
async def trends_news(message: types.Message):
    await message.answer("📈 Ищу самые свежие новости по ЭПР...")
    
    try:
        news_items = await news_parser.get_trending_epr_news()
        
        if not news_items:
            await message.answer(
                "📭 Свежих новостей по ЭПР не найдено.\n\n"
                "💡 **Попробуйте:**\n"
                "• Использовать поиск по конкретным запросам\n"
                "• Проверить позже - новости появляются постоянно\n"
                "• Уточнить запрос"
            )
            return
        
        response = "📈 **Самые свежие новости по ЭПР:**\n\n"
        
        for i, item in enumerate(news_items[:6], 1):
            time_indicator = "🆕 ТОЛЬКО ЧТО" if i == 1 else f"📅 {item['date']}"
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"🕒 {time_indicator}\n\n"
        
        response += "💡 Используйте поиск для более точных результатов."
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске трендов: {e}")
        await message.answer("❌ Ошибка при поиске трендов. Попробуйте позже.")

@dp.message(lambda message: message.text == "🔄 Обновить")
async def refresh_news(message: types.Message):
    await message.answer("🔄 Обновляю результаты...")
    await trends_news(message)  # Показываем обновленные тренды

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    # Если после команды есть текст, используем его как запрос
    if len(message.text.split()) > 1:
        query = ' '.join(message.text.split()[1:])
        await perform_search(message, query)
    else:
        await search_news(message)

@dp.message(Command("trends"))
async def cmd_trends(message: types.Message):
    await trends_news(message)

async def perform_search(message: types.Message, query: str):
    """Выполняет поиск и отправляет результаты"""
    await message.answer(f"🔍 Ищу новости по запросу: '{query}'...")
    
    try:
        news_items = await news_parser.search_all_sources(query)
        
        if not news_items:
            await message.answer(
                f"🔍 По запросу '{query}' не найдено новостей.\n\n"
                f"💡 **Попробуйте:**\n"
                f"• Использовать другие ключевые слова\n"
                f"• Более общий запрос\n"
                f"• Посмотреть трендовые новости"
            )
        else:
            response = f"🔍 **Найдено новостей по '{query}':**\n\n"
            
            for i, item in enumerate(news_items[:5], 1):
                freshness = "🆕" if i <= 2 else "⏱️"
                response += f"**{i}. {item['title']}** {freshness}\n"
                response += f"🔗 [Читать]({item['url']})\n"
                response += f"📌 {item['source']}\n"
                response += f"🕒 {item['date']}\n\n"
            
            if len(news_items) > 5:
                response += f"*... и еще {len(news_items) - 5} новостей*"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске.\n\n"
            "💡 **Возможные причины:**\n"
            "• Проблемы с интернет-соединением\n"
            "• Временная недоступность источников\n"
            "• Слишком частые запросы\n\n"
            "🔄 Попробуйте позже или используйте другой запрос."
        )

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if (user_text.startswith('/') or 
        user_text in ["🔍 Поиск новостей", "📈 Тренды ЭПР", "🆘 Помощь", "🔄 Обновить"]):
        return
    
    # Выполняем поиск по текстовому запросу
    await perform_search(message, user_text)

async def main():
    logger.info("Финальный бот запускается...")
    
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
