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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

class SimpleNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    def get_cached_results(self, query):
        cache_key = f"search_{hash(query)}"
        if cache_key in self.cache:
            cache_time, results = self.cache[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=self.cache_timeout):
                return results
        return None

    def set_cached_results(self, query, results):
        cache_key = f"search_{hash(query)}"
        self.cache[cache_key] = (datetime.now(), results)

    async def search_yandex_news(self, query):
        """Прямой поиск в Яндекс.Новостях"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    articles = []
                    
                    # Ищем карточки новостей
                    news_items = soup.find_all('article', class_='mg-card')
                    
                    for item in news_items[:10]:  # Ограничиваем 10 результатами
                        try:
                            # Заголовок
                            title_elem = item.find('h2', class_='mg-card__title') or item.find('a', class_='mg-card__link')
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            
                            # Ссылка
                            link = title_elem.get('href', '')
                            if link.startswith('/'):
                                link = f"https://yandex.ru{link}"
                            elif link.startswith('https://news.yandex.ru/yandsearch?'):
                                # Извлекаем настоящую ссылку из перенаправления Яндекс
                                match = re.search(r'cl4url=([^&]+)', link)
                                if match:
                                    link = urllib.parse.unquote(match.group(1))
                            
                            # Проверяем, что ссылка валидная
                            if link and link.startswith('http') and 'yandex' not in link:
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'source': 'yandex'
                                })
                                
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга карточки Яндекс: {e}")
                            continue
                    
                    logger.info(f"✅ Яндекс.Новости: найдено {len(articles)} статей")
                    return articles
                    
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска Яндекс: {e}")
            return []

    async def search_google_news(self, query):
        """Прямой поиск в Google News"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=ru&gl=RU&ceid=RU:ru"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    articles = []
                    
                    # Ищем карточки новостей в Google News
                    news_items = soup.find_all('article')
                    
                    for item in news_items[:10]:
                        try:
                            # Заголовок
                            title_elem = item.find('h3') or item.find('h4') or item.find('a')
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            
                            # Ссылка
                            link_elem = title_elem.find_parent('a') if title_elem.name != 'a' else title_elem
                            if link_elem and link_elem.get('href'):
                                link = link_elem.get('href')
                                if link.startswith('./'):
                                    link = f"https://news.google.com{link[1:]}"
                                
                                # Google News дает относительные ссылки, которые ведут на их домен
                                # В реальном боте нужно было бы обрабатывать эти ссылки,
                                # но для простоты оставим как есть
                                
                                if link and link.startswith('http'):
                                    articles.append({
                                        'title': title,
                                        'url': link,
                                        'source': 'google'
                                    })
                                    
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга карточки Google: {e}")
                            continue
                    
                    logger.info(f"✅ Google News: найдено {len(articles)} статей")
                    return articles
                    
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска Google: {e}")
            return []

    async def search_bing_news(self, query):
        """Прямой поиск в Bing News"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.bing.com/news/search?q={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    articles = []
                    
                    # Ищем карточки новостей в Bing
                    news_items = soup.find_all('div', class_='news-card') or soup.find_all('div', class_='tile')
                    
                    for item in news_items[:10]:
                        try:
                            # Заголовок
                            title_elem = item.find('a', class_='title') or item.find('h2') or item.find('a')
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            
                            # Ссылка
                            link = title_elem.get('href', '')
                            if link.startswith('/'):
                                link = f"https://www.bing.com{link}"
                            
                            if link and link.startswith('http') and 'bing.com' not in link:
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'source': 'bing'
                                })
                                
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга карточки Bing: {e}")
                            continue
                    
                    logger.info(f"✅ Bing News: найдено {len(articles)} статей")
                    return articles
                    
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска Bing: {e}")
            return []

    async def simple_search(self, query, search_type="all"):
        """
        Простой и прямой поиск новостей
        search_type: "all", "russian", "international"
        """
        # Проверяем кэш
        cache_key = f"{search_type}_{query}"
        cached = self.get_cached_results(cache_key)
        if cached:
            return cached

        logger.info(f"🔍 Начинаем поиск: '{query}' (тип: {search_type})")
        
        all_articles = []
        
        try:
            # Всегда ищем в Яндекс.Новостях для русских запросов
            if search_type in ["all", "russian"]:
                yandex_results = await self.search_yandex_news(query)
                all_articles.extend(yandex_results)
            
            # Для международных или всех - добавляем Google и Bing
            if search_type in ["all", "international"]:
                google_results = await self.search_google_news(query)
                bing_results = await self.search_bing_news(query)
                all_articles.extend(google_results)
                all_articles.extend(bing_results)
                
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске: {e}")
        
        # Убираем дубликаты по URL
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        # Сохраняем в кэш
        self.set_cached_results(cache_key, unique_articles[:8])  # Ограничиваем 8 результатами
        
        logger.info(f"📊 Итоговые результаты: {len(unique_articles)} уникальных статей")
        return unique_articles[:8]

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск новостей")],
        [KeyboardButton(text="🌍 Международные источники")],
        [KeyboardButton(text="📊 Быстрый поиск")]
    ], 
    resize_keyboard=True
)

class SimpleNewsBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.searcher = SimpleNewsSearcher()
        self.user_states = {}  # user_id -> search_type
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "🤖 <b>Простой поиск новостей</b>\n\n"
                "Я ищу новости по вашему запросу в различных источниках.\n\n"
                "🔍 <b>Поиск новостей</b> - российские источники\n"
                "🌍 <b>Международные источники</b> - зарубежные СМИ\n"
                "📊 <b>Быстрый поиск</b> - все источники\n\n"
                "Просто выберите тип поиска и введите запрос!",
                reply_markup=main_keyboard,
                parse_mode="HTML"
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            help_text = """
📖 <b>Простой поиск новостей</b>

<b>Как работает:</b>
1. Вы вводите запрос
2. Я ищу по этому запросу в поисковых системах
3. Показываю найденные статьи

<b>Примеры запросов:</b>
• ЭПР в финансах
• регуляторная песочница
• Банк России новости
• цифровые финансовые активы
• fintech regulation Russia

<b>Типы поиска:</b>
🔍 <b>Поиск новостей</b> - Яндекс.Новости
🌍 <b>Международные источники</b> - Google News, Bing News  
📊 <b>Быстрый поиск</b> - все источники сразу

💡 <b>Совет:</b> Используйте конкретные запросы для лучших результатов!
"""
            await message.answer(help_text, parse_mode="HTML")

        @self.dp.message(lambda message: message.text == "🔍 Поиск новостей")
        async def set_russian_search(message: types.Message):
            self.user_states[message.from_user.id] = "russian"
            await message.answer("🔍 <b>Режим: российские источники</b>\n\nВведите ваш запрос для поиска в Яндекс.Новостях:", parse_mode="HTML")

        @self.dp.message(lambda message: message.text == "🌍 Международные источники")
        async def set_international_search(message: types.Message):
            self.user_states[message.from_user.id] = "international"
            await message.answer("🌍 <b>Режим: международные источники</b>\n\nВведите ваш запрос для поиска в Google News и Bing News:", parse_mode="HTML")

        @self.dp.message(lambda message: message.text == "📊 Быстрый поиск")
        async def set_quick_search(message: types.Message):
            self.user_states[message.from_user.id] = "all"
            await message.answer("📊 <b>Режим: быстрый поиск</b>\n\nВведите ваш запрос для поиска во всех источниках:", parse_mode="HTML")

        @self.dp.message()
        async def handle_search(message: types.Message):
            user_text = message.text.strip()
            
            # Игнорируем команды и кнопки
            if user_text.startswith('/') or user_text in ["🔍 Поиск новостей", "🌍 Международные источники", "📊 Быстрый поиск"]:
                return

            user_id = message.from_user.id
            search_type = self.user_states.get(user_id, "all")  # По умолчанию ищем везде

            await message.answer(f"🔍 <b>Ищу новости по запросу:</b> '{user_text}'\n\n⏳ <i>Это может занять несколько секунд...</i>", parse_mode="HTML")
            
            try:
                # Простой поиск без лишней обработки
                articles = await self.searcher.simple_search(user_text, search_type)
                
                if articles:
                    response = f"📰 <b>Найдено новостей по запросу</b> '{user_text}':\n\n"
                    
                    for i, article in enumerate(articles, 1):
                        # Обрезаем длинные заголовки
                        title = article['title']
                        if len(title) > 100:
                            title = title[:100] + "..."
                            
                        response += f"{i}. {title}\n"
                        response += f"   🔗 {article['url']}\n\n"
                        
                        # Ограничиваем длину сообщения
                        if len(response) > 3000:
                            response += "... (показаны первые результаты)"
                            break
                            
                else:
                    response = f"😔 <b>По запросу</b> '{user_text}' <b>не найдено новостей.</b>\n\n"
                    response += "💡 Попробуйте:\n• Изменить формулировку\n• Использовать другие ключевые слова\n• Проверить запрос на опечатки"
                
                await message.answer(response, parse_mode="HTML")
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска: {e}")
                await message.answer("❌ <b>Произошла ошибка при поиске.</b> Попробуйте позже.", parse_mode="HTML")

    async def start(self):
        logger.info("🚀 Запуск простого бота для поиска новостей...")
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

    async def stop(self):
        await self.searcher.close()
        await self.bot.session.close()

# Запуск бота
async def main():
    bot = SimpleNewsBot()
    try:
        await bot.start()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
