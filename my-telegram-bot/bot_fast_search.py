import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import urllib.parse
from datetime import datetime
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Быстрая клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Быстрый поиск"), KeyboardButton(text="📰 Свежие новости")],
        [KeyboardButton(text="⚡ ЭПР сейчас"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

class FastSearcher:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        
    async def search_duckduckgo(self, query):
        """Быстрый поиск через DuckDuckGo Instant Answer API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"https://api.duckduckgo.com/"
                params = {
                    'q': query,
                    'format': 'json',
                    'no_html': '1',
                    'skip_disambig': '1'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_duckduckgo(data, query)
                    return []
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo timeout")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo error: {e}")
            return []
            
    def _parse_duckduckgo(self, data, query):
        results = []
        
        # Основной ответ
        if data.get('AbstractText'):
            results.append({
                'title': data.get('Heading', 'Ответ'),
                'url': data.get('AbstractURL', f'https://duckduckgo.com/?q={urllib.parse.quote(query)}'),
                'snippet': data.get('AbstractText', '')[:200] + '...',
                'source': 'DuckDuckGo'
            })
        
        # Связанные темы
        for topic in data.get('RelatedTopics', [])[:3]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append({
                    'title': topic.get('Text', '')[:50],
                    'url': topic.get('FirstURL', f'https://duckduckgo.com/?q={urllib.parse.quote(query)}'),
                    'snippet': topic.get('Text', '')[:150],
                    'source': 'DuckDuckGo'
                })
        
        return results
    
    async def get_epr_news(self):
        """Получаем предзаготовленные новости об ЭПР"""
        # В реальном боте здесь можно подключить RSS или API новостей
        news_items = [
            {
                'title': 'Экспериментальные правовые режимы в России',
                'url': 'https://www.garant.ru/news/',
                'snippet': 'Последние изменения в законодательстве об ЭПР',
                'source': 'Гарант',
                'date': 'Сегодня'
            },
            {
                'title': 'Развитие регуляторных песочниц в 2024',
                'url': 'https://www.vedomosti.ru/finance',
                'snippet': 'Новые направления для ЭПР в финансовом секторе',
                'source': 'Ведомости',
                'date': 'Вчера'
            },
            {
                'title': 'ЦБ о цифровых инновациях',
                'url': 'https://www.cbr.ru/press/',
                'snippet': 'Позиция Банка России по экспериментальным режимам',
                'source': 'ЦБ РФ',
                'date': '2 дня назад'
            }
        ]
        return news_items
    
    async def quick_web_search(self, query):
        """Быстрый поиск с готовыми ссылками"""
        encoded_query = urllib.parse.quote(query)
        
        search_engines = [
            {
                'name': '🌐 Google',
                'url': f'https://www.google.com/search?q={encoded_query}',
                'description': 'Поиск по всему интернету'
            },
            {
                'name': '🔍 Яндекс',
                'url': f'https://yandex.ru/search/?text={encoded_query}',
                'description': 'Русскоязычный поиск'
            },
            {
                'name': '📰 Google News',
                'url': f'https://news.google.com/search?q={encoded_query}',
                'description': 'Новости'
            },
            {
                'name': '🦆 DuckDuckGo',
                'url': f'https://duckduckgo.com/?q={encoded_query}',
                'description': 'Анонимный поиск'
            }
        ]
        
        return search_engines
    
    async def search_telegram(self, query):
        """Поиск в Telegram через готовые ссылки"""
        encoded_query = urllib.parse.quote(query)
        
        channels = [
            {
                'name': '📊 Росфинмониторинг',
                'url': 'https://t.me/rosfinmonitoring',
                'description': 'Официальный канал'
            },
            {
                'name': '🏦 Банк России',
                'url': 'https://t.me/centralbank_russia', 
                'description': 'Новости ЦБ'
            },
            {
                'name': '💡 Инновации',
                'url': f'https://t.me/search?q={encoded_query}',
                'description': 'Поиск по Telegram'
            }
        ]
        
        return channels

# Инициализация быстрого поисковика
fast_searcher = FastSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚀 **Быстрый поисковый бот**\n\n"
        "⚡ Мгновенный поиск по:\n"
        "• Интернету и новостям\n" 
        "• Telegram каналам\n"
        "• Тематике ЭПР\n\n"
        "Просто напишите запрос!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
ℹ️ **Быстрая помощь:**

🔍 **Быстрый поиск** - мгновенные результаты
📰 **Свежие новости** - последние новости об ЭПР  
⚡ **ЭПР сейчас** - актуальная информация
ℹ️ **Помощь** - это сообщение

💡 **Просто напишите запрос** - получите ссылки для поиска за 2-3 секунды!

Примеры:
• "ЭПР финансы"
• "регуляторная песочница"
• "новости ЭПР"
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Быстрый поиск")
async def fast_search_menu(message: types.Message):
    await message.answer("🔍 Напишите запрос для мгновенного поиска:")

@dp.message(lambda message: message.text == "📰 Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("📰 Загружаю последние новости об ЭПР...")
    
    try:
        news = await fast_searcher.get_epr_news()
        
        response = "📰 **Последние новости об ЭПР:**\n\n"
        
        for i, item in enumerate(news, 1):
            response += f"{i}. **{item['title']}**\n"
            response += f"   📅 {item['date']} | 📊 {item['source']}\n"
            response += f"   📝 {item['snippet']}\n"
            response += f"   🔗 {item['url']}\n\n"
        
        # Добавляем быстрые ссылки для поиска новостей
        response += "⚡ **Быстрый поиск новостей:**\n"
        response += "• https://news.google.com/search?q=ЭПР+Россия\n"
        response += "• https://yandex.ru/news/search?text=ЭПР\n"
        response += "• https://www.google.com/search?q=ЭПР+новости\n"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки новостей: {e}")
        await message.answer(
            "📰 **Быстрые ссылки для новостей:**\n\n"
            "• Google News: https://news.google.com/search?q=ЭПР\n"
            "• Яндекс.Новости: https://yandex.ru/news/search?text=ЭПР\n"
            "• РБК: https://www.rbc.ru/rbcsearch?query=ЭПР\n"
        )

@dp.message(lambda message: message.text == "⚡ ЭПР сейчас")
async def epr_now(message: types.Message):
    await message.answer("⚡ Собираю актуальную информацию об ЭПР...")
    
    try:
        # Быстрый поиск по ЭПР
        search_results = await fast_searcher.quick_web_search("ЭПР экспериментальный правовой режим Россия 2024")
        
        response = "⚡ **ЭПР - актуальная информация:**\n\n"
        response += "🔗 **Основные источники:**\n"
        response += "• Росфинмониторинг: https://rosfinmonitoring.ru\n"
        response += "• Банк России: https://cbr.ru/fintech/\n"
        response += "• Правительство РФ: http://government.ru\n\n"
        
        response += "🔍 **Быстрый поиск:**\n"
        for engine in search_results[:3]:
            response += f"• {engine['name']}: {engine['url']}\n"
        
        response += "\n📢 **Telegram каналы:**\n"
        response += "• Росфинмониторинг: https://t.me/rosfinmonitoring\n"
        response += "• Банк России: https://t.me/centralbank_russia\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка ЭПР поиска: {e}")
        await message.answer(
            "⚡ **ЭПР - быстрые ссылки:**\n\n"
            "🌐 Поиск:\n"
            "• https://www.google.com/search?q=ЭПР+Россия+2024\n"
            "• https://yandex.ru/search/?text=ЭПР+экспериментальный+правовой+режим\n\n"
            "📰 Новости:\n"
            "• https://news.google.com/search?q=ЭПР\n"
            "• https://yandex.ru/news/search?text=ЭПР\n"
        )

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_button(message: types.Message):
    await cmd_help(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["🔍 Быстрый поиск", "📰 Свежие новости", "⚡ ЭПР сейчас", "ℹ️ Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу: '{user_text}'...")
    
    try:
        # Быстрый поиск в интернете
        search_engines = await fast_searcher.quick_web_search(user_text)
        telegram_channels = await fast_searcher.search_telegram(user_text)
        
        response = f"🔍 **Результаты для '{user_text}':**\n\n"
        
        response += "🌐 **Поисковые системы:**\n"
        for engine in search_engines:
            response += f"• {engine['name']}: {engine['url']}\n"
        
        response += "\n📢 **Telegram:**\n"
        for channel in telegram_channels:
            response += f"• {channel['name']}: {channel['url']}\n"
        
        # Добавляем быстрые подсказки
        if any(word in user_text.lower() for word in ['эпр', 'регуляторн', 'песочниц']):
            response += "\n💡 **По теме ЭПР:**\n"
            response += "• Росфинмониторинг: https://rosfinmonitoring.ru\n"
            response += "• ЦБ о финтехе: https://cbr.ru/fintech/\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка быстрого поиска: {e}")
        # Всегда работающий fallback
        encoded_query = urllib.parse.quote(user_text)
        await message.answer(
            f"🔍 **Быстрый поиск '{user_text}':**\n\n"
            f"🌐 Google: https://www.google.com/search?q={encoded_query}\n"
            f"🔍 Яндекс: https://yandex.ru/search/?text={encoded_query}\n"
            f"📰 Новости: https://news.google.com/search?q={encoded_query}\n"
            f"📢 Telegram: https://t.me/search?q={encoded_query}\n"
            f"🦆 DuckDuckGo: https://duckduckgo.com/?q={encoded_query}"
        )

async def main():
    logger.info("🚀 Быстрый бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
EOFcat > bot_fast_search.py << 'EOF'
import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import urllib.parse
from datetime import datetime
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Быстрая клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Быстрый поиск"), KeyboardButton(text="📰 Свежие новости")],
        [KeyboardButton(text="⚡ ЭПР сейчас"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

class FastSearcher:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        
    async def search_duckduckgo(self, query):
        """Быстрый поиск через DuckDuckGo Instant Answer API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"https://api.duckduckgo.com/"
                params = {
                    'q': query,
                    'format': 'json',
                    'no_html': '1',
                    'skip_disambig': '1'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_duckduckgo(data, query)
                    return []
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo timeout")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo error: {e}")
            return []
            
    def _parse_duckduckgo(self, data, query):
        results = []
        
        # Основной ответ
        if data.get('AbstractText'):
            results.append({
                'title': data.get('Heading', 'Ответ'),
                'url': data.get('AbstractURL', f'https://duckduckgo.com/?q={urllib.parse.quote(query)}'),
                'snippet': data.get('AbstractText', '')[:200] + '...',
                'source': 'DuckDuckGo'
            })
        
        # Связанные темы
        for topic in data.get('RelatedTopics', [])[:3]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append({
                    'title': topic.get('Text', '')[:50],
                    'url': topic.get('FirstURL', f'https://duckduckgo.com/?q={urllib.parse.quote(query)}'),
                    'snippet': topic.get('Text', '')[:150],
                    'source': 'DuckDuckGo'
                })
        
        return results
    
    async def get_epr_news(self):
        """Получаем предзаготовленные новости об ЭПР"""
        # В реальном боте здесь можно подключить RSS или API новостей
        news_items = [
            {
                'title': 'Экспериментальные правовые режимы в России',
                'url': 'https://www.garant.ru/news/',
                'snippet': 'Последние изменения в законодательстве об ЭПР',
                'source': 'Гарант',
                'date': 'Сегодня'
            },
            {
                'title': 'Развитие регуляторных песочниц в 2024',
                'url': 'https://www.vedomosti.ru/finance',
                'snippet': 'Новые направления для ЭПР в финансовом секторе',
                'source': 'Ведомости',
                'date': 'Вчера'
            },
            {
                'title': 'ЦБ о цифровых инновациях',
                'url': 'https://www.cbr.ru/press/',
                'snippet': 'Позиция Банка России по экспериментальным режимам',
                'source': 'ЦБ РФ',
                'date': '2 дня назад'
            }
        ]
        return news_items
    
    async def quick_web_search(self, query):
        """Быстрый поиск с готовыми ссылками"""
        encoded_query = urllib.parse.quote(query)
        
        search_engines = [
            {
                'name': '🌐 Google',
                'url': f'https://www.google.com/search?q={encoded_query}',
                'description': 'Поиск по всему интернету'
            },
            {
                'name': '🔍 Яндекс',
                'url': f'https://yandex.ru/search/?text={encoded_query}',
                'description': 'Русскоязычный поиск'
            },
            {
                'name': '📰 Google News',
                'url': f'https://news.google.com/search?q={encoded_query}',
                'description': 'Новости'
            },
            {
                'name': '🦆 DuckDuckGo',
                'url': f'https://duckduckgo.com/?q={encoded_query}',
                'description': 'Анонимный поиск'
            }
        ]
        
        return search_engines
    
    async def search_telegram(self, query):
        """Поиск в Telegram через готовые ссылки"""
        encoded_query = urllib.parse.quote(query)
        
        channels = [
            {
                'name': '📊 Росфинмониторинг',
                'url': 'https://t.me/rosfinmonitoring',
                'description': 'Официальный канал'
            },
            {
                'name': '🏦 Банк России',
                'url': 'https://t.me/centralbank_russia', 
                'description': 'Новости ЦБ'
            },
            {
                'name': '💡 Инновации',
                'url': f'https://t.me/search?q={encoded_query}',
                'description': 'Поиск по Telegram'
            }
        ]
        
        return channels

# Инициализация быстрого поисковика
fast_searcher = FastSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚀 **Быстрый поисковый бот**\n\n"
        "⚡ Мгновенный поиск по:\n"
        "• Интернету и новостям\n" 
        "• Telegram каналам\n"
        "• Тематике ЭПР\n\n"
        "Просто напишите запрос!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
ℹ️ **Быстрая помощь:**

🔍 **Быстрый поиск** - мгновенные результаты
📰 **Свежие новости** - последние новости об ЭПР  
⚡ **ЭПР сейчас** - актуальная информация
ℹ️ **Помощь** - это сообщение

💡 **Просто напишите запрос** - получите ссылки для поиска за 2-3 секунды!

Примеры:
• "ЭПР финансы"
• "регуляторная песочница"
• "новости ЭПР"
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Быстрый поиск")
async def fast_search_menu(message: types.Message):
    await message.answer("🔍 Напишите запрос для мгновенного поиска:")

@dp.message(lambda message: message.text == "📰 Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("📰 Загружаю последние новости об ЭПР...")
    
    try:
        news = await fast_searcher.get_epr_news()
        
        response = "📰 **Последние новости об ЭПР:**\n\n"
        
        for i, item in enumerate(news, 1):
            response += f"{i}. **{item['title']}**\n"
            response += f"   📅 {item['date']} | 📊 {item['source']}\n"
            response += f"   📝 {item['snippet']}\n"
            response += f"   🔗 {item['url']}\n\n"
        
        # Добавляем быстрые ссылки для поиска новостей
        response += "⚡ **Быстрый поиск новостей:**\n"
        response += "• https://news.google.com/search?q=ЭПР+Россия\n"
        response += "• https://yandex.ru/news/search?text=ЭПР\n"
        response += "• https://www.google.com/search?q=ЭПР+новости\n"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки новостей: {e}")
        await message.answer(
            "📰 **Быстрые ссылки для новостей:**\n\n"
            "• Google News: https://news.google.com/search?q=ЭПР\n"
            "• Яндекс.Новости: https://yandex.ru/news/search?text=ЭПР\n"
            "• РБК: https://www.rbc.ru/rbcsearch?query=ЭПР\n"
        )

@dp.message(lambda message: message.text == "⚡ ЭПР сейчас")
async def epr_now(message: types.Message):
    await message.answer("⚡ Собираю актуальную информацию об ЭПР...")
    
    try:
        # Быстрый поиск по ЭПР
        search_results = await fast_searcher.quick_web_search("ЭПР экспериментальный правовой режим Россия 2024")
        
        response = "⚡ **ЭПР - актуальная информация:**\n\n"
        response += "🔗 **Основные источники:**\n"
        response += "• Росфинмониторинг: https://rosfinmonitoring.ru\n"
        response += "• Банк России: https://cbr.ru/fintech/\n"
        response += "• Правительство РФ: http://government.ru\n\n"
        
        response += "🔍 **Быстрый поиск:**\n"
        for engine in search_results[:3]:
            response += f"• {engine['name']}: {engine['url']}\n"
        
        response += "\n📢 **Telegram каналы:**\n"
        response += "• Росфинмониторинг: https://t.me/rosfinmonitoring\n"
        response += "• Банк России: https://t.me/centralbank_russia\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка ЭПР поиска: {e}")
        await message.answer(
            "⚡ **ЭПР - быстрые ссылки:**\n\n"
            "🌐 Поиск:\n"
            "• https://www.google.com/search?q=ЭПР+Россия+2024\n"
            "• https://yandex.ru/search/?text=ЭПР+экспериментальный+правовой+режим\n\n"
            "📰 Новости:\n"
            "• https://news.google.com/search?q=ЭПР\n"
            "• https://yandex.ru/news/search?text=ЭПР\n"
        )

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_button(message: types.Message):
    await cmd_help(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["🔍 Быстрый поиск", "📰 Свежие новости", "⚡ ЭПР сейчас", "ℹ️ Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу: '{user_text}'...")
    
    try:
        # Быстрый поиск в интернете
        search_engines = await fast_searcher.quick_web_search(user_text)
        telegram_channels = await fast_searcher.search_telegram(user_text)
        
        response = f"🔍 **Результаты для '{user_text}':**\n\n"
        
        response += "🌐 **Поисковые системы:**\n"
        for engine in search_engines:
            response += f"• {engine['name']}: {engine['url']}\n"
        
        response += "\n📢 **Telegram:**\n"
        for channel in telegram_channels:
            response += f"• {channel['name']}: {channel['url']}\n"
        
        # Добавляем быстрые подсказки
        if any(word in user_text.lower() for word in ['эпр', 'регуляторн', 'песочниц']):
            response += "\n💡 **По теме ЭПР:**\n"
            response += "• Росфинмониторинг: https://rosfinmonitoring.ru\n"
            response += "• ЦБ о финтехе: https://cbr.ru/fintech/\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка быстрого поиска: {e}")
        # Всегда работающий fallback
        encoded_query = urllib.parse.quote(user_text)
        await message.answer(
            f"🔍 **Быстрый поиск '{user_text}':**\n\n"
            f"🌐 Google: https://www.google.com/search?q={encoded_query}\n"
            f"🔍 Яндекс: https://yandex.ru/search/?text={encoded_query}\n"
            f"📰 Новости: https://news.google.com/search?q={encoded_query}\n"
            f"📢 Telegram: https://t.me/search?q={encoded_query}\n"
            f"🦆 DuckDuckGo: https://duckduckgo.com/?q={encoded_query}"
        )

async def main():
    logger.info("🚀 Быстрый бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
