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

# ===== УЛУЧШЕННЫЙ КЛАСС ПОИСКА НОВОСТЕЙ =====
class ImprovedNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300
        # Расширенный список российских доменов с приоритетом официальных источников
        self.russian_domains = [
            'cbr.ru', 'banki.ru', 'government.ru', 'kremlin.ru', 'minfin.ru',  # Официальные источники
            'rbc.ru', 'vedomosti.ru', 'kommersant.ru', 'ria.ru', 'tass.ru',
            'rt.com', 'lenta.ru', 'gazeta.ru', 'iz.ru', 'mk.ru', 'aif.ru',
            'rg.ru', 'vesti.ru', 'newsru.com', 'fontanka.ru', 'ng.ru',
            'echo.msk.ru', 'bfm.ru', 'forbes.ru', 'vc.ru', 'rb.ru',
            'yandex.ru', 'mail.ru', 'rambler.ru', 'interfax.ru', 'banknn.ru',
            'sputniknews.com', 'rbth.com', 'russian.rt.com', 'themoscowtimes.com',
            'finmarket.ru', 'bankir.ru', 'kommersant.ru', 'vedomosti.ru'  # Добавлены финансовые источники
        ]
        # Приоритетные домены (официальные источники)
        self.priority_domains = ['cbr.ru', 'banki.ru', 'government.ru', 'kremlin.ru', 'minfin.ru', 'interfax.ru']
        
        # Черный список паттернов для URL (общие новостные страницы)
        self.url_blacklist_patterns = [
            r'/news/?$', r'/latest/?$', r'/trending/?$', r'/top-news/?$',
            r'/headlines/?$', r'/breaking/?$', r'/updates/?$', r'/analysis/?$',
            r'/market-news/?$', r'/section/', r'/category/', r'/tag/', r'/topic/',
            r'news\.google\.com$', r'news\.google\.com/',
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

    def is_russian_domain(self, url):
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            return any(russian_domain in domain for russian_domain in self.russian_domains)
        except BaseException:
            return False

    def is_priority_domain(self, url):
        """Проверяет, является ли домен приоритетным (официальные источники)"""
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            return any(priority_domain in domain for priority_domain in self.priority_domains)
        except BaseException:
            return False

    def is_russian_text(self, text):
        return bool(re.search('[а-яА-Я]', text))

    def is_specific_article_url(self, url):
        """
        Проверяет, является ли URL конкретной статьей, а не общей новостной страницей
        """
        try:
            url_lower = url.lower()
            parsed = urllib.parse.urlparse(url_lower)
            path = parsed.path
            
            # Проверяем черный список паттернов
            for pattern in self.url_blacklist_patterns:
                if re.search(pattern, url_lower):
                    return False
            
            # Проверяем, что URL содержит признаки конкретной статьи
            article_indicators = [
                r'/\d{4}/', r'/\d{2}/',  # содержит дату
                r'-\d+\.', r'/\d+',      # содержит цифры (ID статьи)
                r'\.html', r'\.php', r'\.aspx',  # конкретная страница
                r'/article/', r'/story/', r'/news/', r'/post/',  # пути статей
            ]
            
            for indicator in article_indicators:
                if re.search(indicator, url_lower):
                    return True
            
            # Если URL короткий (меньше 40 символов), вероятно это не статья
            if len(url) < 40:
                return False
                
            # Если путь содержит много слешей, вероятно это статья
            if path.count('/') >= 3:
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Ошибка проверки URL: {e}")
            return True  # В случае ошибки принимаем URL

    def normalize_title(self, title):
        """Нормализация заголовка для сравнения"""
        if not title:
            return ""
        
        normalized = title.lower()
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        stop_words = ['новости', 'сегодня', 'сейчас', 'последние', 'свежие']
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        return ' '.join(filtered_words)

    def is_duplicate_article(self, article, existing_articles, similarity_threshold=0.8):
        """Проверяет, является ли статья дубликатом существующих"""
        if not article or not existing_articles:
            return False
        
        new_title_normalized = self.normalize_title(article.get('title', ''))
        new_url = article.get('url', '')
        
        for existing in existing_articles:
            existing_title_normalized = self.normalize_title(existing.get('title', ''))
            existing_url = existing.get('url', '')
            
            if self.is_same_domain(new_url, existing_url):
                if self.calculate_similarity(new_title_normalized, existing_title_normalized) > similarity_threshold:
                    return True
            
            if self.calculate_similarity(new_title_normalized, existing_title_normalized) > 0.9:
                return True
        
        return False

    def is_same_domain(self, url1, url2):
        """Проверяет, принадлежат ли URL одному домену"""
        try:
            domain1 = urllib.parse.urlparse(url1).netloc
            domain2 = urllib.parse.urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False

    def calculate_similarity(self, text1, text2):
        """Вычисляет схожесть двух текстов"""
        if not text1 or not text2:
            return 0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0

    async def correct_spelling_auto(self, text):
        """Автоматическая проверка правописания через Yandex Speller API"""
        try:
            if not self.is_russian_text(text):
                return text
                
            session = await self.get_session()
            encoded_text = urllib.parse.quote(text)
            
            url = f"https://speller.yandex.net/services/spellservice.json/checkText?text={encoded_text}&lang=ru,en"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    corrections = await response.json()
                    
                    if corrections:
                        corrected_text = text
                        for correction in reversed(corrections):
                            if correction.get('s'):
                                fixed_word = correction['s'][0]
                                wrong_word = correction['word']
                                corrected_text = corrected_text.replace(wrong_word, fixed_word)
                        
                        logger.info(f"📝 Исправлено правописание: '{text}' -> '{corrected_text}'")
                        return corrected_text
                    
            return text
        except Exception as e:
            logger.error(f"❌ Ошибка проверки правописания: {e}")
            return text

    async def translate_to_english_auto(self, text):
        """Автоматический перевод на английский"""
        try:
            if not self.is_russian_text(text):
                return text
                
            session = await self.get_session()
            encoded_text = urllib.parse.quote(text)
            
            # Используем бесплатный API перевода
            url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=ru|en"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('responseData', {}).get('translatedText'):
                        translated = data['responseData']['translatedText']
                        logger.info(f"🌍 Автоперевод: '{text}' -> '{translated}'")
                        return translated
            
            return text
        except Exception as e:
            logger.error(f"❌ Ошибка перевода: {e}")
            return text

    async def prepare_international_query(self, query):
        """Подготавливает запрос для международного поиска"""
        try:
            logger.info(f"🔧 Подготовка запроса: '{query}'")
            corrected_query = await self.correct_spelling_auto(query)
            translated_query = await self.translate_to_english_auto(corrected_query)
            logger.info(f"✅ Подготовленный запрос: '{translated_query}'")
            return translated_query
            
        except Exception as e:
            logger.error(f"❌ Ошибка подготовки запроса: {e}")
            return query

    async def search_yandex_regular(self, query):
        """Поиск через обычный Яндекс с фильтрацией новостных сайтов"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            # Используем обычный поиск Яндекс
            url = f"https://yandex.ru/search/?text={encoded_query}&lr=213&numdoc=50"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://yandex.ru/',
                'Cache-Control': 'no-cache'
            }

            async with session.get(url, headers=headers, timeout=25) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    
                    # Ищем все органические результаты поиска
                    search_results = soup.find_all('li', class_='serp-item')
                    
                    # Альтернативные селекторы для результатов
                    if not search_results:
                        search_results = soup.find_all('div', class_='organic')
                    if not search_results:
                        search_results = soup.find_all('div', class_=re.compile(r'organic|result'))
                    
                    logger.info(f"🔍 Найдено результатов поиска: {len(search_results)}")

                    for result in search_results[:30]:  # Обрабатываем первые 30 результатов
                        try:
                            # Ищем заголовок
                            title_elem = (result.find('h2') or 
                                        result.find('a', class_='organic__url') or
                                        result.find('a', class_=re.compile(r'link|title')) or
                                        result.find('a', attrs={'href': True}))
                            
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            
                            # Ищем ссылку
                            link = title_elem.get('href', '')
                            
                            # Обрабатываем относительные ссылки Яндекс
                            if link.startswith('/'):
                                link = f"https://yandex.ru{link}"
                            elif link.startswith('//'):
                                link = f"https:{link}"
                            
                            # Пропускаем ссылки на сам Яндекс и другие поисковые системы
                            if any(domain in link for domain in ['yandex.ru', 'google.com', 'bing.com']):
                                continue
                            
                            # Ключевые слова в URL, указывающие на новостные источники
                            news_keywords = ['press', 'news', 'novosti', 'article', 'stati', 'zhurnal', 'doc', 'documents']
                            
                            # Проверяем, что это российский домен И содержит признаки новостного источника
                            if (link and link.startswith('http') and 
                                self.is_russian_domain(link) and
                                any(keyword in link.lower() for keyword in news_keywords)):
                                
                                # Проверяем релевантность по заголовку
                                title_lower = title.lower()
                                query_lower = query.lower()
                                
                                query_words = set(query_lower.split())
                                title_words = set(title_lower.split())
                                common_words = query_words.intersection(title_words)
                                
                                # Считаем релевантность (чем больше общих слов, тем лучше)
                                relevance_score = len(common_words)
                                
                                # Дополнительные баллы за приоритетные домены
                                if self.is_priority_domain(link):
                                    relevance_score += 3
                                
                                # Минимальный порог релевантности
                                if relevance_score >= 1:
                                    articles.append({
                                        'title': title,
                                        'url': link,
                                        'language': 'ru',
                                        'priority': self.is_priority_domain(link),
                                        'relevance_score': relevance_score
                                    })
                                    
                        except Exception as e:
                            logger.debug(f"Ошибка обработки результата: {e}")
                            continue

                    # Сортируем по релевантности и приоритету
                    articles.sort(key=lambda x: (x.get('priority', False), x.get('relevance_score', 0)), reverse=True)
                    
                    # Убираем дубликаты по URL
                    unique_articles = []
                    seen_urls = set()
                    for article in articles:
                        if article['url'] not in seen_urls:
                            seen_urls.add(article['url'])
                            unique_articles.append(article)
                    
                    logger.info(f"✅ Яндекс поиск с фильтром новостей: найдено {len(unique_articles)} статей")
                    return unique_articles[:10]  # Возвращаем топ-10
                    
            return []
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при поиске в Яндекс")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка Яндекс поиска: {e}")
            return []

    async def search_bing_news_improved(self, query, market='ru-RU', exclude_russian=False):
        """Улучшенный поиск в Bing News"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            if market == 'en-US':
                url = f"https://www.bing.com/news/search?q={encoded_query}&cc=us&setlang=en"
            else:
                url = f"https://www.bing.com/news/search?q={encoded_query}&cc={market}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9' if market == 'en-US' else 'ru-RU,ru;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []

                    # Расширяем поиск карточек
                    news_cards = soup.find_all('div', class_='news-card')[:15]
                    if not news_cards:
                        news_cards = soup.find_all('div', class_='tile')[:15]
                    if not news_cards:
                        news_cards = soup.find_all('article')[:15]

                    for card in news_cards:
                        try:
                            title_elem = (card.find('a', class_='title') or
                                        card.find('a', class_=re.compile('title')) or
                                        card.find('h2') or
                                        card.find('h3') or
                                        card.find('a', attrs={'href': True}))

                            if title_elem and title_elem.get('href'):
                                title = title_elem.get_text().strip()
                                url = title_elem.get('href')

                                if url.startswith('/'):
                                    url = f"https://www.bing.com{url}"

                                # Проверяем, что это конкретная статья
                                if url and url.startswith('http') and self.is_specific_article_url(url):
                                    # Для международного поиска пропускаем русские домены
                                    if exclude_russian and self.is_russian_domain(url):
                                        continue
                                        
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'language': 'en' if market == 'en-US' else 'ru',
                                        'priority': self.is_priority_domain(url)
                                    })
                        except Exception:
                            continue

                    return articles
            return []
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при поиске в Bing News")
            return []
        except Exception as e:
            logger.debug(f"Ошибка Bing News: {e}")
            return []

    async def search_google_news_international(self, query):
        """Улучшенный поиск в Google News для международных источников"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    # Ищем все статьи
                    news_articles = soup.find_all('article')[:20]

                    for article in news_articles:
                        try:
                            # Ищем заголовок
                            title_elem = article.find('h3') or article.find('h4') or article.find('a')
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            
                            # Ищем ссылку
                            link_elem = article.find('a')
                            if link_elem and link_elem.get('href'):
                                relative_url = link_elem.get('href')
                                # Преобразуем относительную ссылку в абсолютную
                                if relative_url.startswith('./'):
                                    full_url = f"https://news.google.com{relative_url[1:]}"
                                else:
                                    full_url = f"https://news.google.com{relative_url}" if relative_url.startswith('/') else relative_url
                                
                                # Пропускаем ссылки на сам Google News
                                if 'news.google.com' in full_url:
                                    continue
                                    
                                # Пропускаем русские домены
                                if self.is_russian_domain(full_url):
                                    continue
                                
                                # Проверяем, что это конкретная статья
                                if self.is_specific_article_url(full_url):
                                    articles.append({
                                        'title': title,
                                        'url': full_url,
                                        'language': 'en',
                                        'source': 'google'
                                    })
                                
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга статьи Google: {e}")
                            continue

                    logger.info(f"✅ Google News International: найдено {len(articles)} статей")
                    return articles
                    
            return []
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при поиске в Google News International")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка Google News International: {e}")
            return []

    async def search_duckduckgo_international(self, query):
        """Улучшенный поиск в DuckDuckGo для международных источников"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}+news&kl=us-en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    results = soup.find_all('div', class_='result')[:15]

                    for result in results:
                        try:
                            title_elem = result.find('a', class_='result__a')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                url = title_elem.get('href', '')

                                # Обрабатываем DuckDuckGo redirect
                                if 'duckduckgo.com' in url:
                                    match = re.search(r'uddg=([^&]+)', url)
                                    if match:
                                        url = urllib.parse.unquote(match.group(1))

                                # Пропускаем поисковые страницы и русские домены
                                if any(domain in url for domain in ['google.com/search', 'bing.com/search', 'yandex.ru/search']):
                                    continue
                                    
                                if self.is_russian_domain(url):
                                    continue

                                # Проверяем, что это конкретная статья
                                if url and url.startswith('http') and self.is_specific_article_url(url):
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'language': 'en',
                                        'source': 'duckduckgo'
                                    })
                        except Exception:
                            continue

                    logger.info(f"✅ DuckDuckGo International: найдено {len(articles)} статей")
                    return articles
            return []
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при поиске в DuckDuckGo")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка DuckDuckGo International: {e}")
            return []

    async def search_only_russian(self, query):
        """УЛУЧШЕННЫЙ поиск ТОЛЬКО в российских новостных источниках"""
        cache_key = f"russian_only_{hash(query)}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            logger.info("✅ Используем кэшированные результаты (только российские новости)")
            return cached_results

        logger.info(f"🔍 УЛУЧШЕННЫЙ поиск ТОЛЬКО в российских новостных источниках: {query}")

        try:
            # ОСНОВНОЕ ИЗМЕНЕНИЕ: используем улучшенный Яндекс поиск с фильтрацией новостей
            yandex_results = await self.search_yandex_regular(query)
            logger.info(f"✅ Яндекс поиск (новости): {len(yandex_results)} статей")

            # УПРОЩЕННАЯ фильтрация - принимаем только новостные статьи
            filtered_results = []
            seen_urls = set()
            
            for result in yandex_results:
                if result and result.get('url'):
                    url = result['url'].lower()
                    
                    # Проверяем, что URL содержит признаки новостного источника
                    news_keywords = ['press', 'news', 'novosti', 'article', 'stati', 'zhurnal', 'doc', 'documents']
                    is_news_url = any(keyword in url for keyword in news_keywords)
                    
                    if (url.startswith('http') and 
                        url not in seen_urls and 
                        is_news_url):
                        
                        seen_urls.add(url)
                        filtered_results.append(result)

            # Сортируем: сначала приоритетные, потом по релевантности
            priority_articles = [r for r in filtered_results if r.get('priority') or self.is_priority_domain(r['url'])]
            regular_articles = [r for r in filtered_results if not (r.get('priority') or self.is_priority_domain(r['url']))]
            
            # Сортируем регулярные статьи по релевантности
            regular_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Объединяем с приоритетом официальных источников
            final_results = priority_articles + regular_articles
            
            # Возвращаем результаты
            final_results = final_results[:8]
            
            self.set_cached_results(cache_key, final_results)
            logger.info(f"📊 Итоговые российские новостные результаты: {len(final_results)} статей (приоритетных: {len(priority_articles)})")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка в поиске российских новостей: {e}")
            return []

    async def search_international_only(self, query):
        """Поиск ТОЛЬКО в международных источниках"""
        cache_key = f"international_only_{hash(query)}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            logger.info("✅ Используем кэшированные результаты (международные)")
            return cached_results

        logger.info(f"🌍 Поиск в международных источниках: {query}")

        all_results = []

        try:
            # Подготавливаем запрос для международного поиска
            international_query = await self.prepare_international_query(query)
            logger.info(f"🌍 Подготовленный запрос: {international_query}")

            # Поиск в международных источниках
            google_results = await self.search_google_news_international(international_query)
            all_results.extend(google_results)
            logger.info(f"✅ Google News International: {len(google_results)} статей")

            bing_en_results = await self.search_bing_news_improved(international_query, 'en-US', exclude_russian=True)
            all_results.extend(bing_en_results)
            logger.info(f"✅ Bing International: {len(bing_en_results)} статей")

            duckduckgo_results = await self.search_duckduckgo_international(international_query)
            all_results.extend(duckduckgo_results)
            logger.info(f"✅ DuckDuckGo International: {len(duckduckgo_results)} статей")

        except Exception as e:
            logger.error(f"❌ Ошибка в международном поиске: {e}")

        # Фильтрация только международных источников и конкретных статей
        filtered_results = []
        seen_urls = set()
        
        for result in all_results:
            if result and result.get('url'):
                url = result['url'].lower()
                
                # Пропускаем русские домены и проверяем, что это конкретная статья
                if not self.is_russian_domain(url) and url.startswith('http') and url not in seen_urls and self.is_specific_article_url(url):
                    seen_urls.add(url)
                    filtered_results.append(result)

        # Ограничиваем количество результатов
        final_results = filtered_results[:10]
        
        self.set_cached_results(cache_key, final_results)
        logger.info(f"📊 Итоговые международные результаты: {len(final_results)} статей")
        return final_results

    async def universal_search(self, query, search_type="all"):
        cache_key = f"{search_type}_{query}"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            logger.info("✅ Используем кэшированные результаты")
            return cached_results

        all_results = []

        try:
            if search_type in ["all", "russian"]:
                logger.info(f"🔍 Поиск в российских источниках: {query}")

                # ОСНОВНОЕ ИЗМЕНЕНИЕ: используем улучшенный Яндекс поиск
                yandex_results = await self.search_yandex_regular(query)
                all_results.extend(yandex_results)
                logger.info(f"✅ Яндекс поиск: {len(yandex_results)} статей")

                bing_ru_results = await self.search_bing_news_improved(query, 'ru-RU')
                all_results.extend(bing_ru_results)
                logger.info(f"✅ Bing Россия: {len(bing_ru_results)} статей")

            if search_type in ["all", "international"]:
                logger.info(f"🌍 Поиск в международных источниках: {query}")

                international_results = await self.search_international_only(query)
                all_results.extend(international_results)
                logger.info(f"✅ Все международные источники: {len(international_results)} статей")

        except Exception as e:
            logger.error(f"❌ Ошибка в универсальном поиске: {e}")

        # Упрощенная фильтрация - только по уникальности URL и конкретным статьям
        filtered_results = []
        seen_urls = set()
        
        for result in all_results:
            if result and result.get('url') and result['url'] not in seen_urls and self.is_specific_article_url(result['url']):
                seen_urls.add(result['url'])
                filtered_results.append(result)

        # Сортируем по приоритету для российских источников
        if search_type in ["all", "russian"]:
            priority_articles = [r for r in filtered_results if r.get('priority') or (r.get('language') == 'ru' and self.is_priority_domain(r['url']))]
            regular_articles = [r for r in filtered_results if r not in priority_articles]
            filtered_results = priority_articles + regular_articles

        self.set_cached_results(cache_key, filtered_results[:15])
        logger.info(f"📊 Итоговые уникальные результаты: {len(filtered_results)} статей")
        return filtered_results[:15]

    async def get_fresh_news_today(self):
        cache_key = "fresh_news_today"
        cached_results = self.get_cached_results(cache_key)
        if cached_results:
            return cached_results

        logger.info("🔍 Поиск свежих новостей за сегодня...")

        today_queries = [
            "ЭПР сегодня",
            "ЭПР новости сегодня", 
            "регуляторная песочница сегодня",
            "экспериментальный правовой режим новости",
            "цифровые финансовые активы",
            "регуляторные песочницы Россия",
            "Банк России ЭПР",
            "ЦБ РФ экспериментальный правовой режим"
        ]

        all_articles = []

        for query in today_queries:
            try:
                logger.info(f"📢 Поиск свежих новостей: {query}")

                # ОСНОВНОЕ ИЗМЕНЕНИЕ: используем улучшенный Яндекс поиск
                yandex_results = await self.search_yandex_regular(query)
                bing_results = await self.search_bing_news_improved(query, 'ru-RU')

                for article in yandex_results + bing_results:
                    if not self.is_duplicate_article(article, all_articles) and self.is_specific_article_url(article['url']):
                        all_articles.append(article)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Ошибка при поиске свежих новостей: {e}")
                continue

        # Упрощенная фильтрация
        filtered_articles = []
        seen_urls = set()
        
        for article in all_articles:
            if article and article.get('url') and article['url'] not in seen_urls and self.is_specific_article_url(article['url']):
                seen_urls.add(article['url'])
                filtered_articles.append(article)

        # Сортируем по приоритету
        priority_articles = [a for a in filtered_articles if a.get('priority') or self.is_priority_domain(a.get('url', ''))]
        regular_articles = [a for a in filtered_articles if a not in priority_articles]
        
        filtered_articles = priority_articles + regular_articles

        if len(filtered_articles) < 4:
            logger.info("🔍 Дополнительный поиск свежих новостей...")
            backup_queries = [
                "ЭПР", 
                "регуляторная песочница Россия",
                "экспериментальный правовой режим",
                "цифровая валюта ЦБ",
                "Банк России новости регулирования"
            ]
            
            for query in backup_queries:
                try:
                    backup_results = await self.universal_search(query, "all")
                    for article in backup_results:
                        if article['url'] not in seen_urls and self.is_specific_article_url(article['url']):
                            seen_urls.add(article['url'])
                            filtered_articles.append(article)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Ошибка дополнительного поиска: {e}")

        def relevance_score(article):
            title = article.get('title', '').lower()
            score = 0
            keywords = ['эпр', 'экспериментальный правовой режим', 'регуляторная песочница', 
                       'цифровая валюта', 'цб рф', 'финтех', 'блокчейн', 'банк россии', 'cbr.ru']
            
            for keyword in keywords:
                if keyword in title:
                    score += 1
                    
            # Дополнительные баллы за приоритетные источники
            if article.get('priority') or self.is_priority_domain(article.get('url', '')):
                score += 2
                
            return score

        filtered_articles.sort(key=relevance_score, reverse=True)
        final_articles = filtered_articles[:8]

        self.set_cached_results(cache_key, final_articles)

        logger.info(f"✅ Найдено уникальных свежих новостей: {len(final_articles)}")
        return final_articles

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

# ===== УЛУЧШЕННЫЙ ROBUST BOT CLASS =====
class RobustBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.news_searcher = ImprovedNewsSearcher()
        self._is_running = False
        self._shutdown_event = asyncio.Event()
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "Универсальный поиск новостей об ЭПР\n\n"
                "🔍 Поиск новостей – только российские источники\n"
                "🌍 Международные источники – только зарубежные СМИ\n"
                "⚡ Свежие новости – актуальные статьи\n"
                "📊 Быстрый поиск – российские и международные источники\n\n"
                "💡 Примеры запросов:\n"
                "• ЭПР в финансах\n"
                "• регуляторная песочница\n" 
                "• цифровые финансовые активы\n"
                "• Банк России ЭПР\n\n"
                "Напишите /help для подробной инструкции",
                reply_markup=main_keyboard
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            help_text = """<b>📖 Универсальный поиск новостей об ЭПР</b>

<b>Доступные команды:</b>
/start - начать работу с ботом
/help - показать эту справку

<b>Режимы поиска:</b>
🔍 <b>Поиск новостей</b> - ТОЛЬКО российские источники
🌍 <b>Международные источники</b> - только зарубежные СМИ  
⚡ <b>Свежие новости</b> - поиск актуальных статей за сегодня
📊 <b>Быстрый поиск</b> - российские и международные источники

<b>💡 Примеры успешных запросов:</b>

<b>Короткие запросы:</b>
• ЭПР
• регуляторная песочница  
• Банк России
• финтех регулирование

<b>Конкретные запросы:</b>
• ЭПР в банковской сфере
• экспериментальный правовой режим ЦБ
• цифровые финансовые активы законодательство

<b>Международные запросы:</b>
• Russia fintech sandbox
• digital financial assets Russia
• Bank of Russia regulation

<b>⚡ Советы для лучших результатов:</b>
• Используйте короткие запросы (2-5 слов)
• Для официальных источников: \"Банк России ЭПР\"
• Указывайте конкретные термины: \"цифровые финансовые активы\"
• Для международных: английские термины"""
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
            await message.answer("🌍 Напишите запрос для поиска в международных источниках (автоматический перевод на английский):")

        @self.dp.message(lambda message: message.text == "⚡ Свежие новости")
        async def fresh_news(message: types.Message):
            await message.answer("⚡ Ищу самые свежие новости")
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
                    response = "😔 Не удалось найти свежие новости за сегодня.\n\n"
                    response += "💡 Попробуйте использовать поиск по конкретному запросу."
                await message.answer(response)
            except Exception as e:
                logger.error(f"❌ Ошибка поиска свежих новостей: {e}")
                await message.answer("❌ Ошибка при поиске свежих новостей. Попробуйте позже.")

        @self.dp.message(lambda message: message.text == "📊 Быстрый поиск")
        async def quick_search(message: types.Message):
            user_id = message.from_user.id
            user_search_type[user_id] = 'quick'
            await message.answer("📊 Напишите запрос для быстрого поиска по всем источникам (российские и международные):")

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
                # Быстрый поиск: российские + международные источники
                russian_articles = await self.news_searcher.universal_search(user_text, "russian")
                international_articles = await self.news_searcher.search_international_only(user_text)
                
                if russian_articles or international_articles:
                    response = f"🔍 Результаты быстрого поиска по '{user_text}':\n\n"
                    
                    if russian_articles:
                        response += "🇷🇺 Российские источники:\n\n"
                        for i, article in enumerate(russian_articles[:3], 1):
                            response += f"{i}. {article['title']}\n"
                            response += f"   🔗 {article['url']}\n\n"
                    
                    if international_articles:
                        response += "🌍 Международные источники:\n\n"
                        start_index = len(russian_articles[:3]) + 1
                        for i, article in enumerate(international_articles[:3], start_index):
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
                    for i, article in enumerate(articles[:6], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей в международных источниках.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса или использовать английские термины."
                    
            elif search_type == 'russian':
                # ТОЛЬКО российские источники
                articles = await self.news_searcher.search_only_russian(user_text)
                
                if articles:
                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles[:6], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей в российских источниках.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."
                    
            else:
                # По умолчанию: все источники (для текстовых сообщений без выбора типа)
                articles = await self.news_searcher.universal_search(user_text, "all")
                
                if articles:
                    russian_articles = [a for a in articles if a.get('language') == 'ru']
                    english_articles = [a for a in articles if a.get('language') == 'en']

                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"

                    if russian_articles:
                        response += "🇷🇺 Российские источники:\n\n"
                        for i, article in enumerate(russian_articles[:3], 1):
                            response += f"{i}. {article['title']}\n"
                            response += f"   🔗 {article['url']}\n\n"

                    if english_articles:
                        response += "🌍 Международные источники:\n\n"
                        for i, article in enumerate(english_articles[:3], 1):
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
        """Запуск бота с улучшенной обработкой ошибок"""
        try:
            logger.info("🚀 Запуск бота с разделенным поиском...")
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            self._is_running = True
            self._shutdown_event.clear()
            
            # Polling с улучшенной обработкой ошибок и проверкой shutdown
            while self._is_running and not self._shutdown_event.is_set():
                try:
                    await self.dp.start_polling(
                        self.bot, 
                        skip_updates=True,
                        timeout=10,
                        relax=0.5,
                        allowed_updates=['message', 'callback_query']
                    )
                except asyncio.CancelledError:
                    logger.info("🔄 Поллинг отменен")
                    break
                except Exception as e:
                    if self._is_running and not self._shutdown_event.is_set():
                        logger.error(f"❌ Ошибка в polling: {e}")
                        logger.info("🔄 Перезапуск polling через 3 секунды...")
                        await asyncio.sleep(3)
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Корректная остановка бота"""
        logger.info("🔄 Начинаем остановку бота...")
        self._is_running = False
        self._shutdown_event.set()
        
        try:
            await self.dp.stop_polling()
            logger.info("✅ Поллинг остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке поллинга: {e}")
        
        try:
            await self.news_searcher.close()
            logger.info("✅ Поисковик новостей закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии поисковика: {e}")
        
        try:
            await self.bot.session.close()
            logger.info("✅ Сессия бота закрыта")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии сессии: {e}")
        
        logger.info("✅ Бот корректно остановлен")

# ===== УЛУЧШЕННАЯ ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА =====
async def main():
    """Основная функция запуска бота с улучшенной обработкой SIGTERM"""
    bot_instance = None
    health_server = None
    shutdown_manager = GracefulShutdown()
    
    try:
        # Запускаем health server первым делом
        health_server = HealthServer()
        await health_server.start()
        
        bot_instance = RobustBot()
        
        # Запускаем бота в отдельной task
        bot_task = asyncio.create_task(bot_instance.start())
        
        logger.info("✅ Все сервисы запущены, бот готов к работе")
        
        # Основной цикл проверки состояния
        while not shutdown_manager.shutdown:
            await asyncio.sleep(2)
            
            # Проверяем, жив ли бот и не запрошена ли остановка
            if bot_task.done() and not shutdown_manager.shutdown:
                if bot_task.exception():
                    logger.error(f"❌ Бот упал с ошибкой: {bot_task.exception()}")
                    logger.info("🔄 Перезапускаем бота...")
                    bot_task = asyncio.create_task(bot_instance.start())
                else:
                    logger.warning("⚠️ Бот завершился без ошибки, перезапускаем...")
                    bot_task = asyncio.create_task(bot_instance.start())
        
        # Graceful shutdown при получении SIGTERM
        logger.info("🔄 Начинаем graceful shutdown...")
        
        if bot_instance:
            await bot_instance.stop()
        
        if bot_task and not bot_task.done():
            try:
                await asyncio.wait_for(bot_task, timeout=10.0)
                logger.info("✅ Задача бота завершена")
            except asyncio.TimeoutError:
                logger.warning("⏰ Таймаут ожидания завершения бота, отменяем задачу...")
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    logger.info("✅ Задача бота отменена")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main(): {e}")
    finally:
        # Всегда останавливаем health server
        if health_server:
            await health_server.stop()
        
        if bot_instance:
            await bot_instance.stop()

# ===== ЗАПУСК ПРИЛОЖЕНИЯ С БЕСКОНЕЧНЫМИ ПЕРЕЗАПУСКАМИ =====
if __name__ == "__main__":
    import time
    
    restart_delay = 3  # Начальная задержка в секундах
    max_restart_delay = 300  # Максимальная задержка (5 минут)
    total_restarts = 0  # Счетчик перезапусков для логов
    
    logger.info("♾️ Запуск бота с разделенным поиском и бесконечными перезапусками")
    
    # Бесконечный цикл перезапусков
    while True:
        try:
            total_restarts += 1
            logger.info(f"🔄 Запуск бота (перезапуск #{total_restarts})...")
            
            asyncio.run(main())
            
            # Если main() завершился без исключения, значит бот остановился корректно
            logger.info("✅ Бот завершил работу корректно, перезапускаем через 5 секунд...")
            time.sleep(5)
            restart_delay = 3  # Сбрасываем задержку при успешном завершении
            
        except KeyboardInterrupt:
            logger.info("⏹️ Остановка по запросу пользователя")
            break
            
        except SystemExit as e:
            if e.code == 0:
                logger.info("✅ Нормальное завершение работы, перезапускаем через 5 секунд...")
                time.sleep(5)
                restart_delay = 3
            else:
                logger.error(f"🚨 Аварийное завершение с кодом {e.code}")
                logger.info(f"⏳ Перезапуск через {restart_delay} секунд...")
                time.sleep(restart_delay)
                restart_delay = min(restart_delay * 1.5, max_restart_delay)
                
        except Exception as e:
            logger.error(f"💥 Необработанное исключение: {e}")
            logger.info(f"⏳ Перезапуск через {restart_delay} секунд...")
            time.sleep(restart_delay)
            restart_delay = min(restart_delay * 1.5, max_restart_delay)
    
    logger.info(f"👋 Бот завершил работу после {total_restarts} перезапусков")
