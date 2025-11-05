import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from advanced_news_parser import AdvancedNewsParser, SimpleNewsParser

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверяем токен
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Используем упрощенный парсер для начала
news_parser = SimpleNewsParser()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {user_name}!\n"
        "Я продвинутый бот для поиска новостей об экспериментально-правовых режимах РФ.\n\n"
        "🔍 **Я ищу в:**\n"
        "• Яндекс.Новостях\n"
        "• Google News\n"
        "• RSS лентах СМИ\n"
        "• Официальных сайтах\n"
        "• Telegram каналах\n\n"
        "Используйте /help для списка команд"
    )
    logger.info(f"Пользователь {user_name} запустил бота")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Доступные команды:**\n\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/news - последние новости\n"
        "/search - поиск по ключевым словам\n"
        "/sources - источники поиска\n\n"
        "🔍 **Можно писать запросы текстом:**\n"
        "• 'песочница регуляторная'\n"
        "• 'ЭПР новости'\n"
        "• 'правовой эксперимент'\n"
        "• 'цифровая песочница'\n\n"
        "Я ищу информацию по всем основным источникам!"
    )

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    """Показать последние новости по ключевым словам"""
    await message.answer("🔍 Ищу последние новости о регуляторных песочницах...")
    
    try:
        news_items = await news_parser.search_all_sources("регуляторная песочница")
        
        if not news_items:
            await message.answer(
                "📭 Новостей не найдено.\n\n"
                "Попробуйте:\n"
                "• Использовать команду /search для конкретного запроса\n"
                "• Уточнить запрос\n"
                "• Проверить позже"
            )
            return
        
        response = "📰 **Последние новости:**\n\n"
        
        for i, item in enumerate(news_items[:5], 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"📅 {item['date']}\n\n"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске новостей: {e}")
        await message.answer("❌ Произошла ошибка при поиске новостей. Попробуйте позже.")

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await message.answer(
        "🔍 **Расширенный поиск новостей**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры запросов:\n"
        "• `песочница регуляторная`\n"
        "• `экспериментальный правовой режим`\n"
        "• `ЭПР новости`\n"
        "• `цифровая песочница Москва`",
        parse_mode='Markdown'
    )

@dp.message(Command("sources"))
async def cmd_sources(message: types.Message):
    await message.answer(
        "📚 **Источники поиска:**\n\n"
        "• Яндекс.Новости\n"
        "• Google News\n"
        "• RSS: Lenta.ru, Ведомости, Коммерсант, РИА, ТАСС\n"
        "• Официальные сайты: Digital.gov.ru, Правительство РФ\n"
        "• Telegram каналы органов власти\n\n"
        "🔍 Поиск охватывает последние новости и официальные документы."
    )

@dp.message()
async def handle_text(message: types.Message):
    """Обработка текстовых сообщений для поиска"""
    user_text = message.text.strip()
    
    # Игнорируем команды
    if user_text.startswith('/'):
        return
    
    await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_all_sources(user_text)
        
        if not news_items:
            await message.answer(
                f"🔍 По запросу '{user_text}' ничего не найдено.\n\n"
                "💡 **Попробуйте:**\n"
                "• Использовать другие ключевые слова\n"
                "• Уточнить запрос\n"
                "• Использовать /news для общих новостей"
            )
        else:
            response = f"🔍 **Результаты поиска по '{user_text}':**\n\n"
            
            for i, item in enumerate(news_items[:5], 1):
                response += f"**{i}. {item['title']}**\n"
                response += f"🔗 [Читать]({item['url']})\n"
                response += f"📌 {item['source']}\n"
                response += f"📅 {item['date']}\n\n"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await message.answer("❌ Произошла ошибка при поиске. Попробуйте другой запрос.")

async def main():
    logger.info("Продвинутый бот запускается...")
    
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
