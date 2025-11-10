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

# ===== КОНФИГУРАЦИЯ ЛОГГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
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
    
    def _handle_signal(self, signum, frame):
        logger.info(f"📢 Получен сигнал {signum}, начинаю graceful shutdown...")
        self.shutdown = True

def cleanup_lock():
    try:
        lock_file = "/tmp/telegram-bot.lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info("🔓 Файл блокировки удален")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при удалении lock-файла: {e}")

def check_single_instance():
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
                logger.info("🔄 Старый процесс не найден, продолжаем запуск")
                os.remove(lock_file)
        
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        atexit.register(cleanup_lock)
        logger.info(f"🔒 Файл блокировки создан (PID: {os.getpid()})")
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при проверке блокировки: {e}")

check_single_instance()

# ===== HEALTH CHECK SERVER =====
class HealthServer:
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.runner = None
        self.site = None
    
    async def health_check(self, request):
        return web.Response(text='OK', status=200)
    
    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logger.info(f"🌐 Health server started on port {self.port}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

# ===== ЗАГРУЗКА КОНФИГУРАЦИИ =====
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    sys.exit(1)

# ===== КЛАСС ПОИСКА НОВОСТЕЙ =====
class ImprovedNewsSearcher:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_timeout = 300
        self.russian_domains = [
            'rbc.ru', 'vedomosti.ru', 'kommersant.ru', 'ria.ru', 'tass.ru',
            'rt.com', 'lenta.ru', 'gazeta.ru', 'iz.ru', 'mk.ru', 'aif.ru',
            'rg.ru', 'vesti.ru', 'newsru.com', 'fontanka.ru', 'ng.ru',
            'echo.msk.ru', 'bfm.ru', 'forbes.ru', 'vc.ru', 'rb.ru', 'banki.ru',
            'cbr.ru', 'rosfinmonitoring.ru', 'government.ru', 'kremlin.ru',
            'minfin.ru', 'yandex.ru', 'mail.ru', 'rambler.ru',
            'sputniknews.com', 'rbth.com', 'russian.rt.com', 'themoscowtimes.com'
        ]

    async def get_session(self):
        if self.session is None:
            # Увеличенные таймауты для стабильности
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

    def is_russian_text(self, text):
        return bool(re.search('[а-яА-Я]', text))

    def normalize_title(self, title):
        """Нормализация заголовка для сравнения"""
        if not title:
            return ""
        
        # Приводим к нижнему регистру
        normalized = title.lower()
        
        # Удаляем лишние пробелы
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Удаляем знаки препинания (кроме букв, цифр и пробелов)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Удаляем стоп-слова которые часто повторяются в новостях
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
            
            # Проверяем совпадение по домену и ключевым словам
            if self.is_same_domain(new_url, existing_url):
                # Если URL с одного домена, проверяем схожесть заголовков
                if self.calculate_similarity(new_title_normalized, existing_title_normalized) > similarity_threshold:
                    return True
            
            # Проверяем очень похожие заголовки даже с разных доменов
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
            
            # Yandex Translate API
            url = f"https://translate.yandex.net/api/v1.5/tr.json/translate?key=trnsl.1.1.20230101T000000Z.1234567890.abcdef&lang=ru-en&text={encoded_text}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 200 and data.get('text'):
                        translated = data['text'][0]
                        logger.info(f"🌍 Автоперевод: '{text}' -> '{translated}'")
                        return translated
            
            # Fallback
            return await self.translate_fallback(text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка перевода: {e}")
            return await self.translate_fallback(text)

    async def translate_fallback(self, text):
        """Резервный переводчик"""
        try:
            if not self.is_russian_text(text):
                return text
                
            session = await self.get_session()
            encoded_text = urllib.parse.quote(text)
            
            url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=ru|en"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('responseData', {}).get('translatedText'):
                        translated = data['responseData']['translatedText']
                        logger.info(f"🌍 Резервный перевод: '{text}' -> '{translated}'")
                        return translated
            
            return text
        except Exception as e:
            logger.error(f"❌ Ошибка резервного перевода: {e}")
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

    async def search_yandex_news_direct(self, query):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    news_cards = soup.find_all('article', class_='mg-card')[:10]

                    for card in news_cards:
                        try:
                            title_elem = card.find('h2', class_='mg-card__title') or card.find('a', class_='mg-card__link')
                            if not title_elem:
                                continue

                            title = title_elem.get_text().strip()
                            link = title_elem.get('href', '')

                            if link.startswith('https://news.yandex.ru/yandsearch?'):
                                match = re.search(r'cl4url=([^&]+)', link)
                                if match:
                                    link = urllib.parse.unquote(match.group(1))
                            elif link.startswith('/'):
                                link = f"https://yandex.ru{link}"

                            if link and not any(
                                domain in link for domain in [
                                    'google.com/search',
                                    'yandex.ru/search']):
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'language': 'ru'
                                })
                        except Exception as e:
                            logger.debug(f"Ошибка парсинга карточки Яндекс: {e}")
                            continue

                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Яндекс.Новостей: {e}")
            return []

    async def search_bing_news_improved(self, query, market='ru-RU', exclude_russian=False):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            
            if market == 'en-US':
                url = f"https://www.bing.com/news/search?q={encoded_query}&cc=us&setlang=en"
            else:
                url = f"https://www.bing.com/news/search?q={encoded_query}&cc={market}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9' if market == 'en-US' else 'ru-RU,ru;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []

                    news_cards = soup.find_all('div', class_='news-card')[:10]
                    if not news_cards:
                        news_cards = soup.find_all('div', class_='tile')[:10]
                    if not news_cards:
                        news_cards = soup.find_all('article')[:10]

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

                                if 'bing.com/news/search' in url:
                                    continue

                                if exclude_russian and self.is_russian_domain(url):
                                    continue

                                if exclude_russian and self.is_russian_text(title):
                                    continue

                                if url and not any(
                                    search_domain in url for search_domain in [
                                        'google.com/search',
                                        'bing.com/search']):
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'language': 'en' if market == 'en-US' else 'ru'
                                    })
                        except Exception:
                            continue

                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Bing News: {e}")
            return []

    async def search_google_news_english(self, query, exclude_russian=True):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    news_cards = soup.find_all('article')[:12]

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
                                    
                                    if 'news.google.com' in url:
                                        continue

                                    if exclude_russian and (self.is_russian_domain(url) or self.is_russian_text(title)):
                                        continue

                                    if url and url.startswith('http'):
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

    async def search_duckduckgo_improved(self, query, exclude_russian=True):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}+news&kl=us-en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    articles = []
                    results = soup.find_all('div', class_='result')[:12]

                    for result in results:
                        try:
                            title_elem = result.find('a', class_='result__a')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                url = title_elem.get('href', '')

                                if 'duckduckgo.com' in url:
                                    match = re.search(r'uddg=([^&]+)', url)
                                    if match:
                                        url = urllib.parse.unquote(match.group(1))

                                if any(
                                    domain in url for domain in [
                                        'google.com/search',
                                        'bing.com/search',
                                        'yandex.ru/search']):
                                    continue

                                if exclude_russian and (self.is_russian_domain(url) or self.is_russian_text(title)):
                                    continue

                                if url and url.startswith('http'):
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
            logger.debug(f"Ошибка DuckDuckGo: {e}")
            return []

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

                yandex_results = await self.search_yandex_news_direct(query)
                all_results.extend(yandex_results)
                logger.info(f"✅ Яндекс.Новости: {len(yandex_results)} статей")

                bing_ru_results = await self.search_bing_news_improved(query, 'ru-RU')
                all_results.extend(bing_ru_results)
                logger.info(f"✅ Bing Россия: {len(bing_ru_results)} статей")

            if search_type in ["all", "international"]:
                logger.info(f"🌍 Поиск в международных источниках: {query}")

                international_query = await self.prepare_international_query(query)
                logger.info(f"🌍 Подготовленный запрос: {international_query}")

                google_results = await self.search_google_news_english(international_query, exclude_russian=True)
                all_results.extend(google_results)
                logger.info(f"✅ Google News: {len(google_results)} статей")

                bing_en_results = await self.search_bing_news_improved(international_query, 'en-US', exclude_russian=True)
                all_results.extend(bing_en_results)
                logger.info(f"✅ Bing International: {len(bing_en_results)} статей")

                duckduckgo_results = await self.search_duckduckgo_improved(international_query, exclude_russian=True)
                all_results.extend(duckduckgo_results)
                logger.info(f"✅ DuckDuckGo: {len(duckduckgo_results)} статей")

        except Exception as e:
            logger.error(f"❌ Ошибка в универсальном поиске: {e}")

        # Улучшенная фильтрация дубликатов
        filtered_results = []
        seen_titles = set()
        
        for result in all_results:
            if result and result.get('url'):
                url = result['url'].lower()
                
                # Фильтрация поисковых страниц
                if any(search_domain in url for search_domain in [
                    'google.com/search',
                    'bing.com/search', 
                    'yandex.ru/search',
                    'news.google.com',
                    'news.yandex.ru/yandsearch'
                ]):
                    continue
                
                if search_type == "international":
                    if (self.is_russian_domain(url) or 
                        self.is_russian_text(result.get('title', ''))):
                        continue
                        
                if url.startswith('http') and len(url) > 20:
                    # Проверка на дубликаты по нормализованному заголовку
                    normalized_title = self.normalize_title(result.get('title', ''))
                    if normalized_title and normalized_title not in seen_titles and len(normalized_title) >= 20:
                        seen_titles.add(normalized_title)
                        filtered_results.append(result)

        # Сортируем по релевантности
        filtered_results.sort(key=lambda x: len(x.get('title', '')), reverse=True)
        
        self.set_cached_results(cache_key, filtered_results[:10])
        logger.info(f"📊 Итоговые уникальные результаты: {len(filtered_results)} статей")
        return filtered_results[:10]

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
            "регуляторные песочницы Россия"
        ]

        all_articles = []

        for query in today_queries:
            try:
                logger.info(f"📢 Поиск свежих новостей: {query}")

                yandex_results = await self.search_yandex_news_direct(query)
                bing_results = await self.search_bing_news_improved(query, 'ru-RU')

                # Фильтруем дубликаты на этапе сбора
                for article in yandex_results + bing_results:
                    if not self.is_duplicate_article(article, all_articles):
                        all_articles.append(article)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Ошибка при поиске свежих новостей: {e}")
                continue

        # Улучшенная фильтрация дубликатов
        filtered_articles = []
        seen_titles = set()
        
        for article in all_articles:
            if article and article.get('url'):
                url = article['url'].lower()
                
                # Пропускаем поисковые страницы и некорректные URL
                if any(search_domain in url for search_domain in [
                    'google.com/search', 'bing.com/search', 'yandex.ru/search'
                ]) or len(url) < 20:
                    continue
                
                # Нормализуем заголовок для сравнения
                normalized_title = self.normalize_title(article.get('title', ''))
                
                # Пропускаем статьи с очень короткими заголовками
                if len(normalized_title) < 20:
                    continue
                    
                # Проверяем уникальность по нормализованному заголовку
                if normalized_title not in seen_titles:
                    seen_titles.add(normalized_title)
                    filtered_articles.append(article)

        # Если мало уникальных новостей, делаем дополнительный поиск
        if len(filtered_articles) < 4:
            logger.info("🔍 Дополнительный поиск свежих новостей...")
            backup_queries = [
                "ЭПР", 
                "регуляторная песочница Россия",
                "экспериментальный правовой режим",
                "цифровая валюта ЦБ"
            ]
            
            for query in backup_queries:
                try:
                    backup_results = await self.universal_search(query, "all")
                    for article in backup_results:
                        normalized_title = self.normalize_title(article.get('title', ''))
                        if (normalized_title not in seen_titles and 
                            len(normalized_title) >= 20 and
                            not self.is_duplicate_article(article, filtered_articles)):
                            seen_titles.add(normalized_title)
                            filtered_articles.append(article)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Ошибка дополнительного поиска: {e}")

        # Сортируем по релевантности (приоритет ЭПР и регуляторных тем)
        def relevance_score(article):
            title = article.get('title', '').lower()
            score = 0
            keywords = ['эпр', 'экспериментальный правовой режим', 'регуляторная песочница', 
                       'цифровая валюта', 'цб рф', 'финтех', 'блокчейн']
            
            for keyword in keywords:
                if keyword in title:
                    score += 1
            return score

        filtered_articles.sort(key=relevance_score, reverse=True)
        final_articles = filtered_articles[:8]  # Берем топ-8 самых релевантных

        self.set_cached_results(cache_key, final_articles)

        logger.info(f"✅ Найдено уникальных свежих новостей: {len(final_articles)}")
        return final_articles

    async def close(self):
        if self.session:
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

# ===== ROBUST BOT CLASS =====
class RobustBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.news_searcher = ImprovedNewsSearcher()
        self._is_running = False
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def cmd_start(message: types.Message):
            await message.answer(
                "Универсальный поиск новостей об ЭПР\n\n"
                "🔍 Поиск новостей – российские и международные источники\n"
                "🌍 Международные источники – только зарубежные СМИ\n"
                "⚡ Свежие новости – актуальные статьи\n"
                "📊 Быстрый поиск – мгновенные результаты\n\n"
                "Просто выберите что ищете!",
                reply_markup=main_keyboard
            )

        @self.dp.message(Command("help"))
        async def cmd_help(message: types.Message):
            help_text = """
📖 Универсальный поиск новостей об ЭПР

🔍 Поиск новостей – российские и международные источники
🌍 Международные источники – только зарубежные СМИ
⚡ Свежие новости – поиск актуальных статей за сегодня
📊 Быстрый поиск – мгновенные результаты по всем источникам

💡 Примеры запросов:
    • ЭПР в финансах
• регуляторная песочница
• новые правила ЭПР
• Russia fintech regulation

⚡ Кнопка 'Свежие новости' ищет самые актуальные статьи за сегодня!
"""
            await message.answer(help_text)

        @self.dp.message(lambda message: message.text == "🔍 Поиск новостей")
        async def search_epr_news(message: types.Message):
            user_id = message.from_user.id
            user_search_type[user_id] = 'all'
            await message.answer("🔍 Напишите запрос для поиска новостей:")

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
            await message.answer("📊 Напишите запрос для быстрого поиска по всем источникам:")

        @self.dp.message()
        async def handle_text(message: types.Message):
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
                russian_articles = await self.news_searcher.universal_search(user_text, "russian")
                international_query = await self.news_searcher.prepare_international_query(user_text)
                international_articles = await self.news_searcher.universal_search(international_query, "international")
                articles = russian_articles[:3] + international_articles[:3]
                
                if articles:
                    response = f"🔍 Результаты быстрого поиска по '{user_text}':\n\n"
                    for i, article in enumerate(articles, 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."
                    
            elif search_type == 'international':
                international_query = await self.news_searcher.prepare_international_query(user_text)
                articles = await self.news_searcher.universal_search(international_query, "international")
                
                if articles:
                    response = f"🔍 Результаты поиска по '{user_text}':\n\n"
                    response += "🌍 Международные источники:\n\n"
                    for i, article in enumerate(articles[:6], 1):
                        response += f"{i}. {article['title']}\n"
                        response += f"   🔗 {article['url']}\n\n"
                else:
                    response = f"😔 По запросу '{user_text}' не найдено новостей в международных источниках.\n\n"
                    response += "💡 Попробуйте изменить формулировку запроса."
                    
            else:
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
            logger.info("🚀 Запуск улучшенного поискового бота...")
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            self._is_running = True
            
            # Polling с улучшенной обработкой ошибок
            while self._is_running:
                try:
                    await self.dp.start_polling(
                        self.bot, 
                        skip_updates=True,
                        timeout=60,
                        relax=1,
                        allowed_updates=['message', 'callback_query']
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка в polling: {e}")
                    if self._is_running:  # Перезапускаем только если не запрошен shutdown
                        logger.info("🔄 Перезапуск polling через 5 секунд...")
                        await asyncio.sleep(5)
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Корректная остановка бота"""
        self._is_running = False
        try:
            await self.dp.stop_polling()
            await self.news_searcher.close()
            await self.bot.session.close()
            logger.info("✅ Бот корректно остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")

# ===== ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА =====
async def main():
    """Основная функция запуска бота с улучшенной обработкой ошибок"""
    bot_instance = None
    shutdown_manager = GracefulShutdown()
    
    try:
        bot_instance = RobustBot()
        
        # Запускаем бота в отдельной task для возможности graceful shutdown
        bot_task = asyncio.create_task(bot_instance.start())
        
        # Основной цикл проверки состояния
        while not shutdown_manager.shutdown:
            await asyncio.sleep(5)  # Проверяем каждые 5 секунд
            
            # Проверяем, жив ли бот
            if bot_task.done():
                if bot_task.exception():
                    logger.error(f"❌ Бот упал с ошибкой: {bot_task.exception()}")
                    # Пересоздаем задачу
                    bot_task = asyncio.create_task(bot_instance.start())
                else:
                    logger.warning("⚠️ Бот завершился без ошибки, перезапускаем...")
                    bot_task = asyncio.create_task(bot_instance.start())
        
        # Graceful shutdown
        logger.info("🔄 Начинаем graceful shutdown...")
        if bot_task and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        
        if bot_instance:
            await bot_instance.stop()
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main(): {e}")
        if bot_instance:
            await bot_instance.stop()
        raise

async def main_with_health():
    """Основная функция с health check сервером"""
    health_server = HealthServer()
    await health_server.start()
    
    try:
        await main()
    finally:
        await health_server.stop()

# ===== ЗАПУСК ПРИЛОЖЕНИЯ =====
if __name__ == "__main__":
    import time
    
    restart_count = 0
    max_restarts = 15  # Увеличил лимит перезапусков
    restart_delay = 5
    last_restart_time = time.time()
    
    while restart_count < max_restarts:
        try:
            current_time = time.time()
            # Сбрасываем счетчик, если прошло больше часа с последнего перезапуска
            if current_time - last_restart_time > 3600:
                restart_count = 0
            
            logger.info(f"🔄 Запуск бота (попытка {restart_count + 1}/{max_restarts})...")
            asyncio.run(main_with_health())  # Используем версию с health server
            
        except KeyboardInterrupt:
            logger.info("⏹️ Остановка по запросу пользователя")
            break
            
        except SystemExit as e:
            if e.code == 0:
                logger.info("✅ Нормальное завершение работы")
                break
            else:
                logger.error(f"🚨 Аварийное завершение с кодом {e.code}")
                restart_count += 1
                last_restart_time = time.time()
                
        except Exception as e:
            logger.error(f"💥 Необработанное исключение: {e}")
            restart_count += 1
            last_restart_time = time.time()
            
        if restart_count < max_restarts:
            logger.info(f"⏳ Перезапуск через {restart_delay} секунд...")
            time.sleep(restart_delay)
            # Увеличиваем задержку с каждой попыткой, но не более 120 секунд
            restart_delay = min(restart_delay * 1.5, 120)
    
    if restart_count >= max_restarts:
        logger.error("🚨 Достигнут лимит перезапусков. Бот остановлен.")
    else:
        logger.info("👋 Бот завершил работу")
