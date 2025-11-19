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

# ===== УЛУЧШЕННАЯ КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ===== УЛУЧШЕННАЯ ЗАЩИТА ОТ МНОЖЕСТВЕННОГО ЗАПУСКА =====
class GracefulShutdown:
    def __init__(self):
        self.shutdown = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    
    def _handle_signal(self, signum, frame):
        logger.info(f"📢 Получен сигнал {signum}, начинаю graceful shutdown...")
        self.shutdown = True

def cleanup_lock():
    """Удаление файла блокировки при завершении"""
    try:
        lock_file = "/tmp/telegram-bot.lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info("🔓 Файл блокировки удален")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при удалении lock-файла: {e}")

def kill_previous_instances():
    """Принудительное завершение предыдущих процессов бота без psutil"""
    try:
        current_pid = os.getpid()
        script_name = "universal_search_bot.py"
        
        # Используем pgrep для поиска процессов с нашим скриптом
        try:
            result = subprocess.run(
                ['pgrep', '-f', script_name], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    pid = pid.strip()
                    if pid and pid != str(current_pid):
                        logger.info(f"🚫 Завершаем предыдущий процесс бота: PID {pid}")
                        try:
                            # Сначала пытаемся корректно завершить
                            os.kill(int(pid), signal.SIGTERM)
                            time.sleep(2)
                            
                            # Проверяем, завершился ли процесс
                            try:
                                os.kill(int(pid), 0)
                                # Если процесс еще жив, принудительно завершаем
                                os.kill(int(pid), signal.SIGKILL)
                                logger.info(f"💀 Принудительно завершен процесс: PID {pid}")
                            except ProcessLookupError:
                                logger.info(f"✅ Процесс завершен корректно: PID {pid}")
                                
                        except (ProcessLookupError, ValueError) as e:
                            logger.debug(f"Процесс уже завершен: {pid}")
                            
        except FileNotFoundError:
            logger.warning("⚠️ pgrep не найден, пропускаем завершение предыдущих процессов")
            
        # Альтернативный метод через ps
        try:
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if script_name in line and str(current_pid) not in line:
                        parts = line.split()
                        if len(parts) > 1:
                            pid = parts[1]
                            if pid.isdigit() and pid != str(current_pid):
                                logger.info(f"🚫 Завершаем процесс через ps: PID {pid}")
                                try:
                                    os.kill(int(pid), signal.SIGTERM)
                                    time.sleep(1)
                                    try:
                                        os.kill(int(pid), 0)
                                        os.kill(int(pid), signal.SIGKILL)
                                    except ProcessLookupError:
                                        pass
                                except (ProcessLookupError, ValueError):
                                    pass
        except Exception as e:
            logger.debug(f"Ошибка при использовании ps: {e}")
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка в kill_previous_instances: {e}")

def check_single_instance():
    """Улучшенная проверка единственного экземпляра"""
    try:
        lock_file = "/tmp/telegram-bot.lock"
        
        # Сначала пытаемся завершить предыдущие процессы
        kill_previous_instances()
        time.sleep(2)  # Даем время для завершения
        
        # Проверяем существующий lock-файл
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                old_pid = f.read().strip()
            
            try:
                # Проверяем, жив ли процесс
                os.kill(int(old_pid), 0)
                logger.info(f"❌ Бот уже запущен в процессе {old_pid}. Завершаем.")
                
                # Пытаемся корректно завершить старый процесс
                try:
                    os.kill(int(old_pid), signal.SIGTERM)
                    time.sleep(3)
                except:
                    pass
                    
                # Если процесс все еще жив, принудительно завершаем
                try:
                    os.kill(int(old_pid), 0)
                    os.kill(int(old_pid), signal.SIGKILL)
                    time.sleep(2)
                except:
                    pass
                    
                # Удаляем старый lock-файл
                os.remove(lock_file)
                
            except (ProcessLookupError, ValueError):
                logger.info("🔄 Старый процесс не найден, удаляем lock-файл")
                os.remove(lock_file)
        
        # Создаем новый lock-файл
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        atexit.register(cleanup_lock)
        logger.info(f"🔒 Файл блокировки создан (PID: {os.getpid()})")
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при проверке блокировки: {e}")

# Проверяем единственный экземпляр перед всем остальным
check_single_instance()

# ===== УЛУЧШЕННЫЙ HEALTH CHECK SERVER =====
class HealthServer:
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/readiness', self.readiness_check)
        self.runner = None
        self.site = None
    
    async def health_check(self, request):
        return web.Response(text='OK', status=200)
    
    async def readiness_check(self, request):
        return web.Response(text='READY', status=200)
    
    async def start(self):
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await self.site.start()
            logger.info(f"🌐 Health server started on port {self.port}")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска health server: {e}")
    
    async def stop(self):
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("✅ Health server остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки health server: {e}")

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    sys.exit(1)

# ===== ПРОСТОЙ И РАБОЧИЙ КЛАСС ПОИСКА =====
class SimpleNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300

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

    async def search_yandex_simple(self, query):
        """ПРОСТОЙ И РАБОЧИЙ поиск через Яндекс"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            # Используем обычный поиск Яндекс
            url = f"https://yandex.ru/search/?text={encoded_query}&lr=213"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://yandex.ru/',
                'Cache-Control': 'no-cache',
                'Accept-Encoding': 'gzip, deflate, br'
            }

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Сохраняем HTML для отладки
                    with open('yandex_debug.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    articles = []
                    
                    # ПРОСТОЙ ПАРСИНГ - ищем ВСЕ ссылки в результатах поиска
                    # Ищем все элементы, которые могут быть результатами
                    results = []
                    
                    # Попробуем разные селекторы
                    selectors = [
                        'li.serp-item',
                        'div.organic',
                        'div.serp-item',
                        'div.Result',
                        '.main__content .serp-item',
                        '.serp-list .serp-item'
                    ]
                    
                    for selector in selectors:
                        found = soup.select(selector)
                        if found:
                            results.extend(found)
                            logger.info(f"🔍 Найдено результатов с селектором {selector}: {len(found)}")
                    
                    # Если не нашли стандартными селекторами, ищем по структуре
                    if not results:
                        # Ищем все div и li с классами, содержащими organic или result
                        all_elements = soup.find_all(['div', 'li'])
                        for elem in all_elements:
                            classes = elem.get('class', [])
                            if any(cls for cls in classes if 'organic' in cls or 'result' in cls or 'serp' in cls):
                                results.append(elem)
                        logger.info(f"🔍 Найдено результатов по классам: {len(results)}")
                    
                    logger.info(f"🔍 Всего найдено потенциальных результатов: {len(results)}")

                    for result in results[:15]:  # Обрабатываем первые 15 результатов
                        try:
                            # Ищем ссылку ЛЮБЫМ способом
                            link_elem = None
                            
                            # Пробуем разные способы найти ссылку
                            link_elem = (result.find('a', href=True) or 
                                       result.find('h2').find('a', href=True) if result.find('h2') else None or
                                       result.find('h3').find('a', href=True) if result.find('h3') else None)
                            
                            if not link_elem:
                                # Ищем любую ссылку внутри результата
                                all_links = result.find_all('a', href=True)
                                if all_links:
                                    link_elem = all_links[0]
                            
                            if not link_elem:
                                continue
                                
                            title = link_elem.get_text().strip()
                            link = link_elem.get('href', '')
                            
                            if not title or not link:
                                continue
                            
                            # Обрабатываем относительные ссылки Яндекс
                            if link.startswith('/'):
                                link = f"https://yandex.ru{link}"
                            elif link.startswith('//'):
                                link = f"https:{link}"
                            
                            # Пропускаем ссылки на сам Яндекс
                            if any(domain in link for domain in ['yandex.ru', 'ya.ru']):
                                continue
                            
                            # Проверяем, что это валидный URL
                            if not link.startswith('http'):
                                continue
                            
                            # ПРОСТАЯ ПРОВЕРКА - принимаем ВСЕ российские сайты
                            domain = urllib.parse.urlparse(link).netloc.lower()
                            is_russian = any(ru_domain in domain for ru_domain in [
                                '.ru', '.рф', '.su', 'rbc.ru', 'vedomosti.ru', 'kommersant.ru',
                                'ria.ru', 'tass.ru', 'lenta.ru', 'gazeta.ru', 'interfax.ru'
                            ])
                            
                            if is_russian:
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'language': 'ru'
                                })
                                logger.info(f"✅ Найдена статья: {title[:50]}...")
                                
                        except Exception as e:
                            logger.debug(f"Ошибка обработки результата: {e}")
                            continue

                    logger.info(f"✅ Яндекс поиск: найдено {len(articles)} статей")
                    return articles[:8]  # Возвращаем топ-8
                    
                else:
                    logger.error(f"❌ Яндекс вернул статус: {response.status}")
                    return []
                    
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при поиске в Яндекс")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка Яндекс поиска: {e}")
            return []

    async def search_only_russian(self, query):
        """ПРОСТОЙ поиск ТОЛЬКО в российских источниках"""
        cache_key = f"russian_only_{hash(query)}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            logger.info("✅ Используем кэшированные результаты")
            return cached_results

        logger.info(f"🔍 Поиск в российских источниках: {query}")

        try:
            # Используем простой Яндекс поиск
            articles = await self.search_yandex_simple(query)
            logger.info(f"✅ Найдено статей: {len(articles)}")
            
            # Возвращаем результаты
            self.set_cached_results(cache_key, articles)
            return articles
            
        except Exception as e:
            logger.error(f"❌ Ошибка в поиске российских новостей: {e}")
            return []

    async def search_international_only(self, query):
        """Поиск в международных источниках"""
        logger.info(f"🌍 Поиск в международных источниках: {query}")
        # Пока возвращаем пустой результат для международного поиска
        return []

    async def universal_search(self, query, search_type="all"):
        cache_key = f"{search_type}_{query}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            return cached_results

        articles = []

        try:
            if search_type in ["all", "russian"]:
                logger.info(f"🔍 Поиск в российских источниках: {query}")
                russian_articles = await self.search_only_russian(query)
                articles.extend(russian_articles)

        except Exception as e:
            logger.error(f"❌ Ошибка в универсальном поиске: {e}")

        # Убираем дубликаты по URL
        unique_articles = []
        seen_urls = set()
        
        for article in articles:
            if article and article.get('url') and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        self.set_cached_results(cache_key, unique_articles[:10])
        logger.info(f"📊 Итоговые уникальные результаты: {len(unique_articles)} статей")
        return unique_articles[:10]

    async def get_fresh_news_today(self):
        """Поиск свежих новостей"""
        logger.info("🔍 Поиск свежих новостей за сегодня...")

        today_queries = [
            "ЭПР сегодня",
            "ЭПР новости",
            "регуляторная песочница",
            "экспериментальный правовой режим",
            "цифровые финансовые активы",
            "Банк России ЭПР"
        ]

        all_articles = []

        for query in today_queries:
            try:
                logger.info(f"📢 Поиск свежих новостей: {query}")
                articles = await self.search_yandex_simple(query)
                
                for article in articles:
                    if article['url'] not in [a['url'] for a in all_articles]:
                        all_articles.append(article)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Ошибка при поиске свежих новостей: {e}")
                continue

        # Убираем дубликаты
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            if article and article.get('url') and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        logger.info(f"✅ Найдено уникальных свежих новостей: {len(unique_articles)}")
        return unique_articles[:6]

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔍 Поиск новостей"), 
            KeyboardButton(text="🌍 Международные источники")
        ],
        [
            KeyboardButton(text="⚡ Свежие новости"), 
            KeyboardButton(text="📊 Быстрый поиск")
        ]
    ], 
    resize_keyboard=True
)

user_search_type = {}

# ===== ПРОСТОЙ И РАБОЧИЙ БОТ =====
class SimpleBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.news_searcher = SimpleNewsSearcher()
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "Универсальный поиск новостей об ЭПР\n\n"
                "🔍 Поиск новостей – поиск в российских источниках\n"
                "🌍 Международные источники – поиск в зарубежных СМИ\n"  
                "⚡ Свежие новости – актуальные статьи\n"
                "📊 Быстрый поиск – по всем источникам\n\n"
                "💡 Просто нажмите кнопку и введите запрос",
                reply_markup=main_keyboard
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            help_text = """<b>📖 Универсальный поиск новостей об ЭПР</b>

<b>Доступные команды:</b>
/start - начать работу с ботом
/help - показать эту справку

<b>Режимы поиска:</b>
🔍 <b>Поиск новостей</b> - поиск в российских источниках
🌍 <b>Международные источники</b> - поиск в зарубежных СМИ  
⚡ <b>Свежие новости</b> - поиск актуальных статей
📊 <b>Быстрый поиск</b> - по всем источникам

<b>💡 Примеры запросов:</b>
• ЭПР
• регуляторная песочница  
• Банк России
• цифровые финансовые активы"""
            await message.answer(help_text, parse_mode="HTML")

        @self.dp.message(lambda message: message.text == "🔍 Поиск новостей")
        async def search_epr_news(message: types.Message):
            user_id = message.from_user.id
            user_search_type[user_id] = 'russian'
            await message.answer("🔍 Напишите запрос для поиска новостей в российских источниках:")

        @self.dp.message(lambda message: message.text == "🌍 Международные источники")
        async def international_sources(message: types.Message):
            user_id = message.from_user.id
            user_search_type[user_id] = 'international'
            await message.answer("🌍 Напишите запрос для поиска в международных источниках:")

        @self.dp.message(lambda message: message.text == "⚡ Свежие новости")
        async def fresh_news(message: types.Message):
            await message.answer("⚡ Ищу самые свежие новости...")
            try:
                articles = await self.news_searcher.get_fresh_news_today()
                if articles:
                    response = "⚡ Самые свежие новости:\n\n"
                    for i, article in enumerate(articles, 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                        if len(response) > 3500:
                            response += "... (показаны первые статьи)"
                            break
                else:
                    response = "😔 Не удалось найти свежие новости.\n\n"
                    response += "💡 Попробуйте использовать поиск по конкретному запросу."
                await message.answer(response)
            except Exception as e:
                logger.error(f"❌ Ошибка поиска свежих новостей: {e}")
                await message.answer("❌ Ошибка при поиске свежих новостей. Попробуйте позже.")

        @self.dp.message(lambda message: message.text == "📊 Быстрый поиск")
        async def quick_search(message: types.Message):
            user_id = message.from_user.id
            user_search_type[user_id] = 'quick'
            await message.answer("📊 Напишите запрос для быстрого поиска по всем источникам:")

        @self.dp.message()
        async def handle_text(message: types.Message):
            if self._shutdown_event.is_set():
                await message.answer("❌ Бот находится в режиме остановки. Попробуйте позже.")
                return

            user_text = message.text.strip()
            user_id = message.from_user.id

            buttons = [
                "🔍 Поиск новостей",
                "🌍 Международные источники", 
                "⚡ Свежие новости",
                "📊 Быстрый поиск"]
            if user_text.startswith('/') or user_text in buttons:
                return

            await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")
            await self.process_search(message, user_text, user_id)

    async def process_search(self, message, user_text, user_id):
        try:
            search_type = user_search_type.pop(user_id, 'all')
            
            if search_type == 'quick':
                # Быстрый поиск
                articles = await self.news_searcher.universal_search(user_text, "all")
                
                if articles:
                    response = f"🔍 Результаты быстрого поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles[:5], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."
                    
            elif search_type == 'international':
                # Международные источники
                articles = await self.news_searcher.search_international_only(user_text)
                
                if articles:
                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles[:5], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей в международных источниках.\n\n"
                    response += "💡 Попробуйте использовать российский поиск."
                    
            elif search_type == 'russian':
                # Российские источники
                articles = await self.news_searcher.search_only_russian(user_text)
                
                if articles:
                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles[:5], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей в российских источниках.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."
                    
            else:
                # По умолчанию
                articles = await self.news_searcher.universal_search(user_text, "all")
                
                if articles:
                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles[:5], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."

            await message.answer(response)

        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            await message.answer(f"❌ Ошибка при поиске. Попробуйте другой запрос.")

    async def start(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск простого рабочего бота...")
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            self._is_running = True
            self._shutdown_event.clear()
            
            while self._is_running and not self._shutdown_event.is_set():
                try:
                    await self.dp.start_polling(
                        self.bot, 
                        skip_updates=True,
                        timeout=10,
                        relax=0.5,
                        allowed_updates=['message']
                    )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self._is_running and not self._shutdown_event.is_set():
                        logger.error(f"❌ Ошибка в polling: {e}")
                        await asyncio.sleep(3)
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        logger.info("🔄 Начинаем остановку бота...")
        self._is_running = False
        self._shutdown_event.set()
        
        try:
            await self.dp.stop_polling()
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке поллинга: {e}")
        
        try:
            await self.news_searcher.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии поисковика: {e}")
        
        try:
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии сессии: {e}")
        
        logger.info("✅ Бот корректно остановлен")

# ===== ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА =====
async def main():
    bot_instance = None
    health_server = None
    
    try:
        health_server = HealthServer()
        await health_server.start()
        
        bot_instance = SimpleBot()
        await bot_instance.start()
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main(): {e}")
    finally:
        if health_server:
            await health_server.stop()
        
        if bot_instance:
            await bot_instance.stop()

# ===== ЗАПУСК ПРИЛОЖЕНИЯ =====
if __name__ == "__main__":
    import time
    
    logger.info("🚀 Запуск простого рабочего бота")
    
    while True:
        try:
            asyncio.run(main())
            logger.info("✅ Бот завершил работу корректно, перезапускаем через 5 секунд...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Остановка по запросу пользователя")
            break
            
        except Exception as e:
            logger.error(f"💥 Необработанное исключение: {e}")
            logger.info("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
