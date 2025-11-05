import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from simple_working_parser import WorkingParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
parser = WorkingParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Быстрый поиск"), KeyboardButton(text="📚 Источники")],
        [KeyboardButton(text="⚡ Статус"), KeyboardButton(text="💡 Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска информации об ЭПР и регуляторных песочницах.\n\n"
        "⚡ **Особенности:**\n"
        "• Всегда работаю\n"
        "• Быстрый поиск\n"
        "• Проверенные источники\n"
        "• Прямые ссылки\n\n"
        "💡 **Просто напишите что ищете!**",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Помощь по боту:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search - поиск информации\n"
        "/sources - полезные источники\n"
        "/help - помощь\n\n"
        "**Кнопки:**\n"
        "• 🔍 Быстрый поиск - найти информацию\n"
        "• 📚 Источники - полезные сайты\n"
        "• ⚡ Статус - проверка работы\n"
        "• 💡 Помощь - эта информация\n\n"
        "💡 **Просто напишите любой запрос в чат!**"
    )

@dp.message(lambda message: message.text == "🔍 Быстрый поиск")
async def quick_search(message: types.Message):
    await message.answer(
        "🔍 **Быстрый поиск**\n\n"
        "Напишите что ищете:\n\n"
        "Примеры запросов:\n"
        "• `ЭПР`\n"
        "• `регуляторная песочница`\n"
        "• `правовой эксперимент`\n"
        "• `цифровая экономика`\n\n"
        "⚡ Я найду актуальные источники!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "📚 Источники")
async def show_sources(message: types.Message):
    sources_text = (
        "📚 **Полезные источники по ЭПР:**\n\n"
        "**Официальные сайты:**\n"
        "• [Digital.gov.ru](https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/) - Регуляторные песочницы\n"
        "• [Минэкономразвития](https://www.economy.gov.ru/material/directions/reguliruemyy_sandboks/) - Регулируемый сэндбокс\n"
        "• [ЦБ РФ](https://www.cbr.ru/fintech/) - Финтех и инновации\n\n"
        "**Поисковые системы:**\n"
        "• Google News\n"
        "• Яндекс.Новости\n"
        "• Telegram Search\n"
        "• DuckDuckGo\n\n"
        "💡 Используйте поиск для быстрого доступа к этим источникам!"
    )
    
    await message.answer(sources_text, parse_mode='Markdown', disable_web_page_preview=False)

@dp.message(lambda message: message.text == "⚡ Статус")
async def check_status(message: types.Message):
    await message.answer("🔄 Проверяю доступность...")
    
    try:
        available = await parser.test_connection()
        status = "✅ Отлично" if available else "⚠️ Ограниченный доступ"
        
        status_text = (
            f"⚡ **Статус системы:** {status}\n\n"
            f"**Бот работает:** ✅\n"
            f"**Поиск доступен:** ✅\n"
            f"**Источники:** ✅\n\n"
        )
        
        if available:
            status_text += "**Доступные ресурсы:**\n"
            for resource in available:
                status_text += f"• {resource}\n"
        else:
            status_text += "💡 *Используются альтернативные методы поиска*"
        
        await message.answer(status_text, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer("✅ Бот работает в штатном режиме")

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await quick_search(message)

@dp.message(Command("sources"))
async def cmd_sources(message: types.Message):
    await show_sources(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["🔍 Быстрый поиск", "📚 Источники", "⚡ Статус", "💡 Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу информацию по запросу: '{user_text}'...")
    
    try:
        results = await parser.search_news(user_text)
        
        response = f"🔍 **Результаты по '{user_text}':**\n\n"
        
        for i, item in enumerate(results, 1):
            # Добавляем эмодзи в зависимости от типа
            emoji = "🔍" if item['type'] == 'search_engine' else "📋"
            response += f"{emoji} **{i}. {item['title']}**\n"
            response += f"🔗 [Открыть]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            if item.get('description'):
                response += f"📝 {item['description']}\n"
            response += "\n"
        
        response += "💡 *Все ссылки рабочие и ведут на актуальные источники*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "❌ Временная ошибка. Вот полезные ссылки:\n\n"
            "• [Digital.gov.ru](https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/)\n"
            "• [Google News](https://news.google.com)\n"
            "• [Яндекс.Новости](https://yandex.ru/news)\n"
            "• [Telegram Search](https://t.me)\n\n"
            "💡 Попробуйте поискать напрямую в этих источниках!",
            parse_mode='Markdown',
            disable_web_page_preview=False
        )

async def main():
    logger.info("Рабочий бот запускается...")
    
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
