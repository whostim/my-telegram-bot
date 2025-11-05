import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from powerful_news_parser import PowerfulNewsParser, SimplePowerfulParser

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверяем токен
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Выбираем парсер в зависимости от наличия Telegram API
if os.getenv('API_ID') and os.getenv('API_HASH'):
    news_parser = PowerfulNewsParser()
    logger.info("Using PowerfulNewsParser with Telegram support")
else:
    news_parser = SimplePowerfulParser()
    logger.info("Using SimplePowerfulParser (Telegram API not configured)")

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📰 Свежие новости"), KeyboardButton(text="🔍 Поиск")],
        [KeyboardButton(text="🚀 Тренды"), KeyboardButton(text="ℹ️ О боте")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {user_name}!\n"
        "Я мощный бот для поиска актуальных новостей об экспериментально-правовых режимах РФ.\n\n"
        "🔍 **Я ищу в реальном времени:**\n"
        "• 100+ Telegram каналов\n"
        "• Google News & Яндекс.Новости\n"
        "• RSS ведущих СМИ\n"
        "• Социальные сети\n\n"
        "🕒 **Только свежие новости (за последние 24 часа)**",
        reply_markup=main_keyboard
    )
    logger.info(f"Пользователь {user_name} запустил бота")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Доступные команды:**\n\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/news - свежие новости\n"
        "/trends - трендовые новости\n"
        "/search - расширенный поиск\n\n"
        "🔍 **Используйте кнопки или пишите запросы:**\n"
        "• 'песочница регуляторная'\n"
        "• 'ЭПР новости'\n"
        "• 'правовой эксперимент'\n\n"
        "⚡ Бот ищет только актуальные новости!"
    )

@dp.message(lambda message: message.text == "📰 Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("🔍 Ищу самые свежие новости о регуляторных песочницах...")
    
    try:
        news_items = await news_parser.search_all_sources("регуляторная песочница", hours_back=24)
        
        if not news_items:
            await message.answer(
                "📭 Свежих новостей не найдено.\n\n"
                "Попробуйте:\n"
                "• Использовать другие ключевые слова\n"
                "• Посмотреть трендовые новости\n"
                "• Проверить позже - новости обновляются постоянно"
            )
            return
        
        response = "📰 **Самые свежие новости:**\n\n"
        
        for i, item in enumerate(news_items[:6], 1):
            time_ago = "только что" if i == 1 else "недавно"
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"🕒 {item['date']} ({time_ago})\n\n"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске свежих новостей: {e}")
        await message.answer("❌ Произошла ошибка при поиске. Попробуйте позже.")

@dp.message(lambda message: message.text == "🚀 Тренды")
async def trends_news(message: types.Message):
    await message.answer("📈 Ищу трендовые новости...")
    
    try:
        news_items = await news_parser.get_trending_news()
        
        if not news_items:
            await message.answer(
                "📊 Пока нет трендовых новостей.\n\n"
                "Используйте поиск по конкретным запросам."
            )
            return
        
        response = "📈 **Трендовые новости сейчас:**\n\n"
        
        for i, item in enumerate(news_items[:5], 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"🕒 {item['date']}\n\n"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске трендов: {e}")
        await message.answer("❌ Ошибка при поиске трендов.")

@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_menu(message: types.Message):
    await message.answer(
        "🔍 **Расширенный поиск**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры:\n"
        "• `песочница регуляторная`\n"
        "• `ЭПР Москва`\n"
        "• `правовой эксперимент 2024`\n"
        "• `цифровая песочница новости`\n\n"
        "⚡ Поиск по всем источникам в реальном времени!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    sources_text = (
        "• 100+ Telegram каналов\n"
        "• Google News & Яндекс.Новости\n"
        "• RSS: Lenta.ru, РИА, ТАСС, РБК и др.\n"
        "• Социальные сети\n"
        "• Официальные источники"
    )
    
    await message.answer(
        f"🤖 **Мощный поисковый бот**\n\n"
        f"**Источники:**\n{sources_text}\n\n"
        f"**Особенности:**\n"
        f"• Только свежие новости (0-24 часа)\n"
        f"• Поиск по всем каналам Telegram\n"
        f"• Рейтинги по актуальности\n"
        f"• Мгновенное обновление\n\n"
        f"⚡ Работает в реальном времени!"
    )

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    await fresh_news(message)

@dp.message(Command("trends"))
async def cmd_trends(message: types.Message):
    await trends_news(message)

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_menu(message)

@dp.message()
async def handle_text(message: types.Message):
    """Обработка текстовых запросов"""
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["📰 Свежие новости", "🚀 Тренды", "🔍 Поиск", "ℹ️ О боте"]:
        return
    
    await message.answer(f"🔍 Ищу актуальные новости по запросу: '{user_text}'...")
    
    try:
        # Ищем самые свежие новости (за последние 12 часов)
        news_items = await news_parser.search_all_sources(user_text, hours_back=12)
        
        if not news_items:
            await message.answer(
                f"🔍 По запросу '{user_text}' не найдено актуальных новостей.\n\n"
                "💡 **Попробуйте:**\n"
                "• Использовать другие ключевые слова\n"
                "• Расширить временной диапазон\n"
                "• Посмотреть трендовые новости"
            )
        else:
            response = f"🔍 **Актуальные новости по '{user_text}':**\n\n"
            
            for i, item in enumerate(news_items[:5], 1):
                time_indicator = "🆕" if i == 1 else "⏱️"
                response += f"**{i}. {item['title']}** {time_indicator}\n"
                response += f"🔗 [Читать]({item['url']})\n"
                response += f"📌 {item['source']}\n"
                response += f"🕒 {item['date']}\n\n"
            
            if len(news_items) > 5:
                response += f"*... и еще {len(news_items) - 5} новостей*"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await message.answer("❌ Произошла ошибка при поиске. Попробуйте другой запрос.")

async def main():
    logger.info("Мощный бот запускается...")
    
    # Удаляем вебхук перед запуском polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
