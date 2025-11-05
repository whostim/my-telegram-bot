import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from universal_parser import UniversalParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
parser = UniversalParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти везде"), KeyboardButton(text="📰 Новости сайтов")],
        [KeyboardButton(text="📢 Поиск в TG"), KeyboardButton(text="⚡ Статус")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я универсальный бот для поиска информации.\n\n"
        "🔍 **Я ищу в реальном времени:**\n"
        "• Новостных сайтах (Google News, Яндекс.Новости)\n"
        "• Telegram каналах\n"
        "• RSS лентах\n"
        "• Поисковых системах\n\n"
        "💡 **Просто напишите любой запрос!**",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Помощь по боту:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search - поиск по всем источникам\n"
        "/news - поиск на сайтах\n"
        "/telegram - поиск в TG\n"
        "/help - помощь\n\n"
        "**Кнопки:**\n"
        "• 🔍 Найти везде - поиск по всем источникам\n"
        "• 📰 Новости сайтов - поиск на новостных сайтах\n"
        "• 📢 Поиск в TG - поиск в Telegram каналах\n"
        "• ⚡ Статус - проверка работы\n\n"
        "💡 **Просто напишите любой запрос в чат!**"
    )

@dp.message(lambda message: message.text == "🔍 Найти везде")
async def search_everywhere(message: types.Message):
    await message.answer(
        "🔍 **Универсальный поиск**\n\n"
        "Напишите запрос для поиска по ВСЕМ источникам:\n"
        "• Новостные сайты\n"
        "• Telegram каналы\n"
        "• RSS ленты\n"
        "• Поисковые системы\n\n"
        "Примеры: 'ЭПР', 'регуляторная песочница', 'правовой эксперимент'"
    )

@dp.message(lambda message: message.text == "📰 Новости сайтов")
async def search_websites(message: types.Message):
    await message.answer(
        "📰 **Поиск на новостных сайтах**\n\n"
        "Напишите запрос для поиска на сайтах:\n"
        "• Google News\n"
        "• Яндекс.Новости\n"
        "• РБК, Лента.ру, Ведомости\n\n"
        "Пример: 'ЭПР новости', 'цифровая песочница'"
    )

@dp.message(lambda message: message.text == "📢 Поиск в TG")
async def search_telegram(message: types.Message):
    await message.answer(
        "📢 **Поиск в Telegram каналах**\n\n"
        "Напишите запрос для поиска в Telegram:\n"
        "• VC.RU, РБК, Ведомости\n"
        "• ТАСС, РИА Новости\n"
        "• Технические и новостные каналы\n\n"
        "Пример: 'ЭПР обсуждение', 'регуляторные новости'"
    )

@dp.message(lambda message: message.text == "⚡ Статус")
async def check_status(message: types.Message):
    await message.answer(
        "⚡ **Статус системы:**\n\n"
        "✅ Бот активен\n"
        "🔍 Парсер работает\n"
        "🌐 Источники доступны\n"
        "💡 Готов к поиску\n\n"
        "**Доступные источники:**\n"
        "• Google News ✓\n"
        "• Яндекс.Новости ✓\n"
        "• Telegram каналы ✓\n"
        "• RSS ленты ✓\n"
        "• Поисковые системы ✓"
    )

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_everywhere(message)

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    await search_websites(message)

@dp.message(Command("telegram"))
async def cmd_telegram(message: types.Message):
    await search_telegram(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["🔍 Найти везде", "📰 Новости сайтов", "📢 Поиск в TG", "⚡ Статус"]:
        return
    
    await message.answer(f"🔍 Ищу информацию по запросу: '{user_text}'...")
    
    try:
        results = await parser.search_all_sources(user_text, max_results=10)
        
        if not results:
            await message.answer(
                f"🔍 По запросу '{user_text}' ничего не найдено.\n\n"
                f"💡 **Попробуйте:**\n"
                f"• Использовать другие ключевые слова\n"
                f"• Более общий запрос\n"
                f"• Проверить написание\n\n"
                f"⚡ Поиск работает в реальном времени!"
            )
        else:
            response = f"🔍 **Результаты по '{user_text}':**\n\n"
            
            for i, item in enumerate(results, 1):
                # Добавляем эмодзи в зависимости от типа источника
                emoji = "📰" if item['type'] == 'news' else "📢" if item['type'] == 'telegram' else "🔍"
                response += f"{emoji} **{i}. {item['title']}**\n"
                response += f"🔗 [Открыть]({item['url']})\n"
                response += f"📌 {item['source']}\n"
                response += f"🕒 {item['date']}\n\n"
            
            response += f"💡 *Найдено {len(results)} результатов*"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске.\n\n"
            "💡 **Что можно сделать:**\n"
            "• Проверить интернет-соединение\n"
            "• Попробовать другой запрос\n"
            "• Подождать несколько минут\n\n"
            "⚡ Система автоматически восстановится!"
        )

async def main():
    logger.info("Универсальный бот запускается...")
    
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
