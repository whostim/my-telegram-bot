import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск в интернете"), KeyboardButton(text="📢 Поиск в Telegram")],
        [KeyboardButton(text="⚡ Быстрый поиск ЭПР"), KeyboardButton(text="🌐 Все поисковики")]
    ],
    resize_keyboard=True
)

class UniversalSearcher:
    @staticmethod
    def search_internet(query):
        """Поиск по всему интернету"""
        encoded_query = urllib.parse.quote(query)
        
        searches = [
            {
                "name": "🌐 Google",
                "url": f"https://www.google.com/search?q={encoded_query}+ЭПР+регуляторная+песочница+Россия",
                "description": "Поиск по всем сайтам в Google"
            },
            {
                "name": "🔍 Яндекс",
                "url": f"https://yandex.ru/search/?text={encoded_query}+ЭПР+регуляторная+песочница",
                "description": "Поиск по русскоязычным сайтам"
            },
            {
                "name": "📰 Google News",
                "url": f"https://news.google.com/search?q={encoded_query}+ЭПР+Russia&hl=ru-RU&gl=RU&ceid=RU:ru",
                "description": "Поиск в новостях"
            },
            {
                "name": "📚 Яндекс.Новости",
                "url": f"https://yandex.ru/news/search?text={encoded_query}+ЭПР",
                "description": "Поиск в новостях"
            },
            {
                "name": "🦆 DuckDuckGo",
                "url": f"https://duckduckgo.com/?q={encoded_query}+ЭПР+Россия",
                "description": "Анонимный поиск"
            },
            {
                "name": "🔎 Bing",
                "url": f"https://www.bing.com/search?q={encoded_query}+ЭПР+Russia",
                "description": "Поиск от Microsoft"
            }
        ]
        return searches

    @staticmethod
    def search_telegram(query):
        """Поиск по всему Telegram"""
        encoded_query = urllib.parse.quote(query)
        
        searches = [
            {
                "name": "📢 Telegram Global Search",
                "url": f"https://t.me/search?q={encoded_query}",
                "description": "Поиск по всем публичным каналам Telegram"
            },
            {
                "name": "🔍 Telegram по каналам",
                "url": f"https://t.me/search?q={encoded_query}+ЭПР",
                "description": "Поиск по каналам с тегом ЭПР"
            },
            {
                "name": "💬 Telegram в чатах",
                "url": f"https://t.me/search?q={encoded_query}+песочница",
                "description": "Поиск в чатах и каналах"
            },
            {
                "name": "🌍 Telegram Web",
                "url": f"https://web.telegram.org/k/#search?query={encoded_query}",
                "description": "Веб-версия поиска в Telegram"
            }
        ]
        return searches

    @staticmethod
    def search_epr_quick():
        """Быстрый поиск по ЭПР"""
        searches = [
            {
                "name": "🚀 Все об ЭПР",
                "url": "https://www.google.com/search?q=ЭПР+экспериментальный+правовой+режим+Россия+2024",
                "description": "Полный поиск по теме ЭПР"
            },
            {
                "name": "📰 Новости ЭПР",
                "url": "https://news.google.com/search?q=ЭПР+Россия+2024&hl=ru-RU&gl=RU&ceid=RU:ru",
                "description": "Свежие новости об ЭПР"
            },
            {
                "name": "📢 Telegram ЭПР",
                "url": "https://t.me/search?q=ЭПР+экспериментальный+правовой+режим",
                "description": "Поиск в Telegram по ЭПР"
            },
            {
                "name": "💼 Регуляторные песочницы",
                "url": "https://www.google.com/search?q=регуляторная+песочница+Россия+2024+ЭПР",
                "description": "Поиск по регуляторным песочницам"
            },
            {
                "name": "🔍 Яндекс ЭПР",
                "url": "https://yandex.ru/search/?text=ЭПР+экспериментальный+правовой+режим+2024",
                "description": "Поиск в Яндексе"
            }
        ]
        return searches

searcher = UniversalSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌍 **Универсальный поисковый бот**\n\n"
        "Я ищу по ВСЕМУ интернету и ВСЕМУ Telegram!\n\n"
        "🔍 **Что я умею:**\n"
        "• Искать по всем сайтам интернета\n"
        "• Искать по всем каналам Telegram\n"
        "• Использовать все поисковые системы\n"
        "• Находить самую актуальную информацию\n\n"
        "💡 **Просто напишите что ищете!**",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Помощь по универсальному поиску:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search - поиск в интернете\n"
        "/telegram - поиск в Telegram\n"
        "/epr - быстрый поиск по ЭПР\n"
        "/help - помощь\n\n"
        "**Кнопки:**\n"
        "• 🔍 Поиск в интернете - поиск по всем сайтам\n"
        "• 📢 Поиск в Telegram - поиск по всему TG\n"
        "• ⚡ Быстрый поиск ЭПР - готовые запросы по ЭПР\n"
        "• 🌐 Все поисковики - все системы поиска\n\n"
        "💡 **Просто напишите ЛЮБОЙ запрос в чат!**"
    )

@dp.message(lambda message: message.text == "🔍 Поиск в интернете")
async def search_internet_menu(message: types.Message):
    await message.answer(
        "🔍 **Поиск по всему интернету**\n\n"
        "Напишите запрос для поиска:\n\n"
        "Примеры:\n"
        "• `ЭПР новости`\n"
        "• `регуляторная песочница`\n"
        "• `правовой эксперимент 2024`\n"
        "• `любой ваш запрос`\n\n"
        "🌐 Я найду по всем поисковым системам!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "📢 Поиск в Telegram")
async def search_telegram_menu(message: types.Message):
    await message.answer(
        "📢 **Поиск по всему Telegram**\n\n"
        "Напишите запрос для поиска в Telegram:\n\n"
        "Примеры:\n"
        "• `ЭПР обсуждение`\n"
        "• `песочница регуляторная`\n"
        "• `цифровая экономика`\n"
        "• `любой запрос`\n\n"
        "💬 Я найду по всем публичным каналам TG!",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "⚡ Быстрый поиск ЭПР")
async def quick_search_epr(message: types.Message):
    searches = searcher.search_epr_quick()
    
    response = "⚡ **Быстрый поиск по ЭПР:**\n\n"
    
    for i, search in enumerate(searches, 1):
        response += f"**{i}. {search['name']}**\n"
        response += f"🔗 [Открыть поиск]({search['url']})\n"
        response += f"📝 {search['description']}\n\n"
    
    await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)

@dp.message(lambda message: message.text == "🌐 Все поисковики")
async def all_search_engines(message: types.Message):
    await message.answer(
        "🌐 **Все поисковые системы:**\n\n"
        "Напишите запрос для поиска во ВСЕХ системах:\n\n"
        "• Google, Яндекс, Bing, DuckDuckGo\n"
        "• Google News, Яндекс.Новости\n"
        "• Telegram Global Search\n\n"
        "🚀 Максимальный охват поиска!",
        parse_mode='Markdown'
    )

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_internet_menu(message)

@dp.message(Command("telegram"))
async def cmd_telegram(message: types.Message):
    await search_telegram_menu(message)

@dp.message(Command("epr"))
async def cmd_epr(message: types.Message):
    await quick_search_epr(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    buttons = ["🔍 Поиск в интернете", "📢 Поиск в Telegram", "⚡ Быстрый поиск ЭПР", "🌐 Все поисковики"]
    if user_text.startswith('/') or user_text in buttons:
        return
    
    await message.answer(f"🔍 Ищу по всему интернету и Telegram: '{user_text}'...")
    
    try:
        # Поиск в интернете
        internet_searches = searcher.search_internet(user_text)
        # Поиск в Telegram
        telegram_searches = searcher.search_telegram(user_text)
        
        response = f"🔍 **Результаты поиска по '{user_text}':**\n\n"
        
        response += "**🌐 Поиск в интернете:**\n"
        for i, search in enumerate(internet_searches[:3], 1):
            response += f"{i}. **{search['name']}**\n"
            response += f"🔗 [Открыть]({search['url']})\n"
            response += f"📝 {search['description']}\n\n"
        
        response += "**📢 Поиск в Telegram:**\n"
        for i, search in enumerate(telegram_searches[:2], 1):
            response += f"{i}. **{search['name']}**\n"
            response += f"🔗 [Открыть]({search['url']})\n"
            response += f"📝 {search['description']}\n\n"
        
        response += f"💡 *Найдены ссылки для поиска в {len(internet_searches) + len(telegram_searches)} системах*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=False)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "❌ Ошибка при формировании поиска.\n\n"
            "💡 **Прямые ссылки на поиск:**\n"
            f"• [Google](https://www.google.com/search?q={urllib.parse.quote(user_text)})\n"
            f"• [Яндекс](https://yandex.ru/search/?text={urllib.parse.quote(user_text)})\n"
            f"• [Telegram](https://t.me/search?q={urllib.parse.quote(user_text)})\n\n"
            "🚀 Используйте эти ссылки напрямую!",
            parse_mode='Markdown',
            disable_web_page_preview=False
        )

async def main():
    logger.info("🌍 Универсальный поисковый бот запускается...")
    
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
    import asyncio
    asyncio.run(main())
