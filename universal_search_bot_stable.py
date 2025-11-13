from datetime import datetime, timedelta
import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import urllib.parse
from bs4 import BeautifulSoup
import re
import sys
import signal

# ===== УСТОЙЧИВАЯ КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден")
    sys.exit(1)

# ===== УПРОЩЕННЫЙ И УСТОЙЧИВЫЙ КЛАСС ПОИСКА =====
class StableNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=20)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def search_yandex_news(self, query):
        """Поиск в Яндекс.Новостях"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    articles = []
                    
                    news_cards = soup.find_all('article', class_='mg-card')[:6]
                    for card in news_cards:
                        try:
                            title_elem = card.find('h2', class_='mg-card__title') or card.find('a', class_='mg-card__link')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = title_elem.get('href', '')
                                
                                if link.startswith('/'):
                                    link = f"https://yandex.ru{link}"
                                elif link.startswith('https://news.yandex.ru/yandsearch?'):
                                    match = re.search(r'cl4url=([^&]+)', link)
                                    if match:
                                        link = urllib.parse.unquote(match.group(1))
                                
                                if link and 'yandex.ru/search' not in link:
                                    articles.append({
                                        'title': title,
                                        'url': link,
                                        'language': 'ru'
                                    })
                        except Exception:
                            continue
                    
                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Яндекс.Новостей: {e}")
            return []

    async def search_google_news(self, query):
        """Поиск в Google News на английском"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    articles = []
                    
                    news_cards = soup.find_all('article')[:6]
                    for card in news_cards:
                        try:
                            title_elem = card.find('h3') or card.find('h4') or card.find('a', attrs={'href': True})
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link_elem = title_elem.find_parent('a') if title_elem.name != 'a' else title_elem
                                if link_elem and link_elem.get('href'):
                                    url = link_elem.get('href')
                                    if url.startswith('./'):
                                        url = f"https://news.google.com{url[1:]}"
                                    
                                    if 'news.google.com' not in url and url.startswith('http'):
                                        articles.append({
                                            'title': title,
                                            'url': url,
                                            'language': 'en'
                                        })
                        except Exception:
                            continue
                    
                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Google News: {e}")
            return []

    async def search_only_russian(self, query):
        """ТОЛЬКО российские источники"""
        logger.info(f"🔍 Поиск российских новостей: {query}")
        
        articles = await self.search_yandex_news(query)
        
        # Фильтрация результатов
        filtered_articles = []
        seen_urls = set()
        
        for article in articles:
            url = article['url'].lower()
            if (url not in seen_urls and 
                len(article['title']) >= 15 and
                not any(domain in url for domain in ['yandex.ru/search', 'google.com/search'])):
                seen_urls.add(url)
                filtered_articles.append(article)
        
        return filtered_articles[:6]

    async def search_international(self, query):
        """ТОЛЬКО международные источники"""
        logger.info(f"🌍 Поиск международных новостей: {query}")
        
        articles = await self.search_google_news(query)
        
        # Фильтрация результатов
        filtered_articles = []
        seen_urls = set()
        
        for article in articles:
            url = article['url'].lower()
            if (url not in seen_urls and 
                len(article['title']) >= 15 and
                not any(domain in url for domain in ['news.google.com', 'yandex.ru'])):
                seen_urls.add(url)
                filtered_articles.append(article)
        
        return filtered_articles[:6]

    async def quick_search(self, query):
        """Быстрый поиск по всем источникам"""
        logger.info(f"📊 Быстрый поиск: {query}")
        
        russian_task = asyncio.create_task(self.search_only_russian(query))
        international_task = asyncio.create_task(self.search_international(query))
        
        russian_articles, international_articles = await asyncio.gather(
            russian_task, international_task, return_exceptions=True
        )
        
        # Обработка исключений
        if isinstance(russian_articles, Exception):
            logger.error(f"Ошибка российского поиска: {russian_articles}")
            russian_articles = []
        if isinstance(international_articles, Exception):
            logger.error(f"Ошибка международного поиска: {international_articles}")
            international_articles = []
        
        return {
            'russian': russian_articles[:3],
            'international': international_articles[:3]
        }

    async def get_fresh_news(self):
        """Свежие новости"""
        logger.info("⚡ Поиск свежих новостей")
        
        queries = [
            "ЭПР сегодня",
            "регуляторная песочница",
            "экспериментальный правовой режим",
            "цифровые финансовые активы"
        ]
        
        all_articles = []
        for query in queries:
            try:
                articles = await self.search_only_russian(query)
                all_articles.extend(articles)
                await asyncio.sleep(1)  # Задержка между запросами
            except Exception as e:
                logger.error(f"Ошибка при поиске '{query}': {e}")
                continue
        
        # Удаление дубликатов
        unique_articles = []
        seen_titles = set()
        for article in all_articles:
            title = article['title'].lower()
            if title not in seen_titles and len(title) >= 20:
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles[:6]

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# ===== КЛАСС БОТА С УСТОЙЧИВОЙ АРХИТЕКТУРОЙ =====
class StableBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.searcher = StableNewsSearcher()
        self.is_running = False
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔍 Поиск новостей"), KeyboardButton(text="🌍 Международные источники")],
                    [KeyboardButton(text="⚡ Свежие новости"), KeyboardButton(text="📊 Быстрый поиск")]
                ],
                resize_keyboard=True
            )
            
            await message.answer(
                "🤖 Универсальный поиск новостей об ЭПР\n\n"
                "🔍 Поиск новостей – только российские источники\n"
                "🌍 Международные источники – только зарубежные СМИ\n" 
                "⚡ Свежие новости – актуальные статьи за сегодня\n"
                "📊 Быстрый поиск – российские и международные источники\n\n"
                "Выберите тип поиска:",
                reply_markup=keyboard
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            help_text = """
📖 Помощь по боту:

🔍 Поиск новостей – ТОЛЬКО российские источники
🌍 Международные источники – только зарубежные СМИ  
⚡ Свежие новости – самые актуальные статьи
📊 Быстрый поиск – российские и международные источники

💡 Примеры запросов:
• ЭПР в финансах
• регуляторная песочница
• цифровые финансовые активы
• Russia fintech regulation
"""
            await message.answer(help_text)

        @self.dp.message(lambda message: message.text == "🔍 Поиск новостей")
        async def russian_search_handler(message: types.Message):
            await message.answer("🔍 Введите запрос для поиска в российских источниках:")
            self.dp.message.register(self.handle_russian_search)

        @self.dp.message(lambda message: message.text == "🌍 Международные источники")
        async def international_search_handler(message: types.Message):
            await message.answer("🌍 Введите запрос для поиска в международных источниках:")
            self.dp.message.register(self.handle_international_search)

        @self.dp.message(lambda message: message.text == "⚡ Свежие новости")
        async def fresh_news_handler(message: types.Message):
            await message.answer("⚡ Ищу свежие новости...")
            try:
                articles = await self.searcher.get_fresh_news()
                if articles:
                    response = "⚡ Свежие новости:\n\n"
                    for i, article in enumerate(articles, 1):
                        response += f"{i}. {article['title']}\n🔗 {article['url']}\n\n"
                else:
                    response = "😔 Не удалось найти свежие новости. Попробуйте позже."
                await message.answer(response)
            except Exception as e:
                logger.error(f"Ошибка поиска свежих новостей: {e}")
                await message.answer("❌ Ошибка при поиске свежих новостей.")

        @self.dp.message(lambda message: message.text == "📊 Быстрый поиск")
        async def quick_search_handler(message: types.Message):
            await message.answer("📊 Введите запрос для быстрого поиска:")
            self.dp.message.register(self.handle_quick_search)

    async def handle_russian_search(self, message: types.Message):
        """Обработчик поиска в российских источниках"""
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("❌ Запрос слишком короткий.")
            return

        await message.answer(f"🔍 Ищу российские новости по запросу: '{query}'...")
        
        try:
            articles = await self.searcher.search_only_russian(query)
            if articles:
                response = f"🔍 Результаты по '{query}':\n\n🇷🇺 Российские источники:\n\n"
                for i, article in enumerate(articles, 1):
                    response += f"{i}. {article['title']}\n🔗 {article['url']}\n\n"
            else:
                response = f"😔 По запросу '{query}' не найдено новостей в российских источниках."
            
            await message.answer(response)
        except Exception as e:
            logger.error(f"Ошибка российского поиска: {e}")
            await message.answer("❌ Ошибка при поиске. Попробуйте другой запрос.")

        # Удаляем обработчик после использования
        self.dp.message.unregister(self.handle_russian_search)

    async def handle_international_search(self, message: types.Message):
        """Обработчик поиска в международных источниках"""
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("❌ Запрос слишком короткий.")
            return

        await message.answer(f"🌍 Ищу международные новости по запросу: '{query}'...")
        
        try:
            articles = await self.searcher.search_international(query)
            if articles:
                response = f"🔍 Результаты по '{query}':\n\n🌍 Международные источники:\n\n"
                for i, article in enumerate(articles, 1):
                    response += f"{i}. {article['title']}\n🔗 {article['url']}\n\n"
            else:
                response = f"😔 По запросу '{query}' не найдено новостей в международных источниках."
            
            await message.answer(response)
        except Exception as e:
            logger.error(f"Ошибка международного поиска: {e}")
            await message.answer("❌ Ошибка при поиске. Попробуйте другой запрос.")

        # Удаляем обработчик после использования
        self.dp.message.unregister(self.handle_international_search)

    async def handle_quick_search(self, message: types.Message):
        """Обработчик быстрого поиска"""
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("❌ Запрос слишком короткий.")
            return

        await message.answer(f"📊 Быстрый поиск по запросу: '{query}'...")
        
        try:
            results = await self.searcher.quick_search(query)
            
            response = f"📊 Результаты быстрого поиска по '{query}':\n\n"
            
            if results['russian']:
                response += "🇷🇺 Российские источники:\n\n"
                for i, article in enumerate(results['russian'], 1):
                    response += f"{i}. {article['title']}\n🔗 {article['url']}\n\n"
            
            if results['international']:
                response += "🌍 Международные источники:\n\n"
                start_num = len(results['russian']) + 1
                for i, article in enumerate(results['international'], start_num):
                    response += f"{i}. {article['title']}\n🔗 {article['url']}\n\n"
            
            if not results['russian'] and not results['international']:
                response = f"😔 По запросу '{query}' не найдено новостей."
            
            await message.answer(response)
        except Exception as e:
            logger.error(f"Ошибка быстрого поиска: {e}")
            await message.answer("❌ Ошибка при поиске. Попробуйте другой запрос.")

        # Удаляем обработчик после использования
        self.dp.message.unregister(self.handle_quick_search)

    async def start(self):
        """Запуск бота с защитой от падений"""
        try:
            logger.info("🚀 Запуск устойчивого бота...")
            self.is_running = True
            
            # Очистка вебхуков и запуск polling
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(self.bot, skip_updates=True)
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка бота: {e}")
            raise

    async def stop(self):
        """Корректная остановка бота"""
        logger.info("🔄 Остановка бота...")
        self.is_running = False
        
        try:
            await self.dp.stop_polling()
            await self.searcher.close()
            await self.bot.session.close()
            logger.info("✅ Бот корректно остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке: {e}")

# ===== ПРОСТАЯ И УСТОЙЧИВАЯ ОСНОВНАЯ ФУНКЦИЯ =====
async def main():
    """Основная функция с минимальной сложностью"""
    bot = None
    try:
        bot = StableBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка по запросу пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        if bot:
            await bot.stop()

# ===== ОБРАБОТЧИКИ СИГНАЛОВ ДЛЯ RENDER =====
def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"📢 Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# ===== ЗАПУСК ПРИЛОЖЕНИЯ =====
if __name__ == "__main__":
    logger.info("🎯 Запуск устойчивой версии бота")
    
    # Простой запуск без сложных циклов перезапуска
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")
        sys.exit(1)
