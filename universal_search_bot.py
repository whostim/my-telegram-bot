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
import json
import re
import random
import sys
import atexit
import signal
from aiohttp import web
import threading
import subprocess
import time

# ===== КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ===== ЗАЩИТА ОТ МНОЖЕСТВЕННОГО ЗАПУСКА =====
def check_single_instance():
    """Проверка единственного экземпляра"""
    try:
        lock_file = "/tmp/telegram-bot.lock"
        
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                old_pid = f.read().strip()
            
            try:
                os.kill(int(old_pid), 0)
                logger.info(f"❌ Бот уже запущен в процессе {old_pid}. Завершаем.")
                sys.exit(1)
            except (ProcessLookupError, ValueError):
                os.remove(lock_file)
        
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        def cleanup():
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except:
                pass
        
        atexit.register(cleanup)
        logger.info(f"🔒 Файл блокировки создан (PID: {os.getpid()})")
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при проверке блокировки: {e}")

check_single_instance()

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    sys.exit(1)

# ===== РАБОЧИЙ КЛАСС ПОИСКА =====
class WorkingNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            connector = aiohttp.TCPConnector(limit=10, keepalive_timeout=30)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
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

    async def search_yandex_working(self, query):
        """РАБОЧИЙ поиск через Яндекс - имитируем реального пользователя"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            # Используем разные URL Яндекс
            urls = [
                f"https://yandex.ru/search/?text={encoded_query}&lr=213",
                f"https://www.yandex.ru/search/?text={encoded_query}&lr=213",
                f"https://yandex.com/search/?text={encoded_query}&lang=ru"
            ]
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }

            articles = []
            
            for url in urls:
                try:
                    logger.info(f"🔍 Пробуем URL: {url}")
                    
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Сохраняем HTML для отладки
                            with open('yandex_response.html', 'w', encoding='utf-8') as f:
                                f.write(html)
                            
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # ПРОСТОЙ И ЭФФЕКТИВНЫЙ ПАРСИНГ
                            # Ищем ВСЕ ссылки в результатах поиска
                            all_links = soup.find_all('a', href=True)
                            
                            for link in all_links:
                                try:
                                    href = link.get('href', '')
                                    text = link.get_text().strip()
                                    
                                    # Фильтруем только релевантные ссылки
                                    if (href.startswith('http') and 
                                        not any(domain in href for domain in ['yandex.ru', 'ya.ru', 'yandex.com']) and
                                        len(text) > 10 and  # Заголовок достаточно длинный
                                        any(keyword in text.lower() for keyword in ['эпр', 'регулятор', 'финтех', 'банк', 'новости', 'песочница'])):
                                        
                                        # Проверяем российский домен
                                        domain = urllib.parse.urlparse(href).netloc.lower()
                                        if any(ru_domain in domain for ru_domain in ['.ru', '.рф', '.su']):
                                            articles.append({
                                                'title': text,
                                                'url': href,
                                                'language': 'ru'
                                            })
                                            logger.info(f"✅ Найдена статья: {text[:60]}...")
                                            
                                except Exception as e:
                                    continue
                            
                            # Если нашли статьи, выходим
                            if articles:
                                break
                                
                        else:
                            logger.warning(f"⚠️ Статус ответа: {response.status}")
                            
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при запросе к {url}: {e}")
                    continue

            logger.info(f"📊 Всего найдено статей: {len(articles)}")
            return articles[:10]
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    async def search_google_news(self, query):
        """Резервный поиск через Google News"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            url = f"https://news.google.com/rss/search?q={encoded_query}+Россия&hl=ru&gl=RU&ceid=RU:ru"
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'application/rss+xml, text/xml, */*'
            }

            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    soup = BeautifulSoup(xml_content, 'xml')
                    
                    articles = []
                    items = soup.find_all('item')[:10]
                    
                    for item in items:
                        try:
                            title = item.find('title').text if item.find('title') else ''
                            link = item.find('link').text if item.find('link') else ''
                            
                            if title and link:
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'language': 'ru'
                                })
                        except:
                            continue
                    
                    logger.info(f"✅ Google News: найдено {len(articles)} статей")
                    return articles
                    
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка Google News: {e}")
            return []

    async def search_only_russian(self, query):
        """Поиск в российских источниках"""
        cache_key = f"russian_{hash(query)}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            return cached_results

        logger.info(f"🔍 Поиск: {query}")

        articles = []

        try:
            # Основной поиск через Яндекс
            yandex_articles = await self.search_yandex_working(query)
            articles.extend(yandex_articles)
            
            # Если Яндекс не нашел, используем Google News
            if not articles:
                google_articles = await self.search_google_news(query)
                articles.extend(google_articles)
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")

        # Убираем дубликаты
        unique_articles = []
        seen_urls = set()
        
        for article in articles:
            if article and article.get('url') and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        self.set_cached_results(cache_key, unique_articles)
        logger.info(f"📊 Итоговые результаты: {len(unique_articles)} статей")
        return unique_articles

    async def get_fresh_news(self):
        """Свежие новости"""
        logger.info("🔍 Поиск свежих новостей...")

        queries = [
            "ЭПР",
            "регуляторная песочница",
            "экспериментальный правовой режим", 
            "цифровые финансовые активы",
            "Банк России",
            "финтех регулирование"
        ]

        all_articles = []

        for query in queries:
            try:
                articles = await self.search_only_russian(query)
                all_articles.extend(articles)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ Ошибка при поиске {query}: {e}")
                continue

        # Убираем дубликаты
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            if article and article.get('url') and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        logger.info(f"✅ Свежих новостей: {len(unique_articles)}")
        return unique_articles[:8]

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# ===== ТЕЛЕГРАМ БОТ =====
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск новостей")],
        [KeyboardButton(text="⚡ Свежие новости")]
    ], 
    resize_keyboard=True
)

user_search_type = {}

class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.searcher = WorkingNewsSearcher()
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "🔍 Бот для поиска новостей об ЭПР\n\n"
                "🔍 Поиск новостей - найду статьи по вашему запросу\n"
                "⚡ Свежие новости - покажу актуальные статьи\n\n"
                "Просто нажмите кнопку и введите запрос!",
                reply_markup=main_keyboard
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            await message.answer(
                "💡 Как использовать бота:\n\n"
                "1. Нажмите '🔍 Поиск новостей'\n"
                "2. Введите запрос (например: 'ЭПР' или 'регуляторная песочница')\n"
                "3. Бот найдет и покажет актуальные статьи\n\n"
                "Или нажмите '⚡ Свежие новости' для получения последних новостей"
            )

        @self.dp.message(lambda message: message.text == "🔍 Поиск новостей")
        async def search_news(message: types.Message):
            user_search_type[message.from_user.id] = 'search'
            await message.answer("🔍 Введите ваш запрос для поиска новостей:")

        @self.dp.message(lambda message: message.text == "⚡ Свежие новости")
        async def fresh_news(message: types.Message):
            await message.answer("⚡ Ищу свежие новости...")
            
            try:
                articles = await self.searcher.get_fresh_news()
                
                if articles:
                    response = "⚡ Свежие новости:\n\n"
                    for i, article in enumerate(articles, 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"🔗 {article['url']}\n\n"
                        
                        if len(response) > 3000:
                            response += "... (показаны первые статьи)"
                            break
                else:
                    response = "😔 Не удалось найти свежие новости.\n"
                    response += "Попробуйте использовать поиск по конкретному запросу."
                    
                await message.answer(response)
                
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                await message.answer("❌ Ошибка при поиске новостей. Попробуйте позже.")

        @self.dp.message()
        async def handle_message(message: types.Message):
            user_id = message.from_user.id
            text = message.text.strip()

            if text.startswith('/'):
                return

            if user_id in user_search_type and user_search_type[user_id] == 'search':
                del user_search_type[user_id]
                await message.answer(f"🔍 Ищу: '{text}'...")
                
                try:
                    articles = await self.searcher.search_only_russian(text)
                    
                    if articles:
                        response = f"🔍 Результаты по '{text}':\n\n"
                        for i, article in enumerate(articles[:5], 1):
                            response += f"{i}. {article['title']}\n"
                            response += f"🔗 {article['url']}\n\n"
                    else:
                        response = f"😔 По запросу '{text}' ничего не найдено.\n"
                        response += "Попробуйте другой запрос или нажмите '⚡ Свежие новости'"
                        
                    await message.answer(response)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка поиска: {e}")
                    await message.answer("❌ Ошибка при поиске. Попробуйте другой запрос.")
            else:
                await message.answer("ℹ️ Выберите действие с помощью кнопок ниже:", reply_markup=main_keyboard)

    async def start(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск рабочего бота...")
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            raise

    async def stop(self):
        """Остановка бота"""
        await self.searcher.close()
        await self.bot.session.close()

# ===== ЗАПУСК =====
async def main():
    bot = None
    try:
        bot = TelegramBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка по запросу пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        if bot:
            await bot.stop()

if __name__ == "__main__":
    logger.info("🚀 Запуск РАБОЧЕГО бота для поиска новостей")
    asyncio.run(main())
