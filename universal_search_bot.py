from datetime import datetime
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
from datetime import datetime, timedelta

def format_date(date_str):
    if not date_str:
        return ""
    
    # Убираем относительные форматы времени
    relative_patterns = [
        r'\d+\s*(мес|месяц|месяцев|месяца)',
        r'\d+\s*(год|года|лет)',
        r'\d+\s*(день|дня|дней)',
        r'\d+\s*(недел|недели|недель)',
        r'\d+\s*(час|часа|часов)',
        r'\d+\s*(минут|минуты)',
        r'только что',
        r'вчера',
        r'сегодня'
    ]
    
    for pattern in relative_patterns:
        if re.search(pattern, date_str.lower()):
            return ""

    try:
        from datetime import datetime
        formats_to_try = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S'
        ]
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%d.%m.%Y')
            except ValueError:
                continue
    except Exception:
        pass
    return ""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
            timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
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

    def is_russian_domain(self, url):
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            return any(russian_domain in domain for russian_domain in self.russian_domains)
        except BaseException:
            return False

    async def translate_query(self, query):
        translation_dict = {
            'эпр': 'EPR',
            'экспериментальный': 'experimental',
            'правовой': 'legal',
            'режим': 'regime',
            'регуляторная': 'regulatory',
            'песочница': 'sandbox',
            'финансы': 'finance',
            'финтех': 'fintech',
            'банк': 'bank',
            'россия': 'Russia',
            'рф': 'Russian Federation',
            'цифровой': 'digital',
            'экономика': 'economy',
            'инновации': 'innovations',
            'технологии': 'technologies',
            'закон': 'law',
            'правительство': 'government',
            'регулирование': 'regulation'
        }

        words = query.lower().split()
        translated_words = []

        for word in words:
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word in translation_dict:
                translated_words.append(translation_dict[clean_word])
            else:
                translated_words.append(clean_word)

        translated_query = ' '.join(translated_words)

        if any(word in query.lower() for word in ['эпр', 'регуляторная', 'песочница']):
            translated_query += " Russia"

        return translated_query

    async def search_yandex_news_direct(self, query):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers) as response:
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

                            source_elem = card.find('span', class_='mg-card-source__source')
                            time_elem = card.find('span', class_='mg-card-source__time')
                            desc_elem = card.find('div', class_='mg-card__annotation')

                            if link and not any(
                                domain in link for domain in [
                                    'google.com/search',
                                    'yandex.ru/search']):
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'source': source_elem.get_text().strip() if source_elem else 'Яндекс.Новости',
                                    'date': time_elem.get_text().strip() if time_elem else '',
                                    'description': desc_elem.get_text().strip() if desc_elem else '',
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

            async with session.get(url, headers=headers) as response:
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

                                source_elem = card.find(['div', 'span'], class_=re.compile('source|author'))
                                time_elem = card.find(['div', 'span'], class_=re.compile('time|date'))

                                if url and not any(
                                    search_domain in url for search_domain in [
                                        'google.com/search',
                                        'bing.com/search']):
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'source': source_elem.get_text().strip() if source_elem else 'Bing News',
                                        'date': time_elem.get_text().strip() if time_elem else '',
                                        'language': 'en' if market == 'en-US' else 'ru'
                                    })
                        except Exception:
                            continue

                    return articles
            return []
        except Exception as e:
            logger.debug(f"Ошибка Bing News: {e}")
            return []

    async def search_google_news_english(self, query):
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }

            async with session.get(url, headers=headers) as response:
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

                                    if self.is_russian_domain(url):
                                        continue

                                    time_elem = card.find('time')
                                    source_elem = card.find(['div', 'span'], class_=re.compile('source'))

                                    if url and url.startswith('http'):
                                        articles.append({
                                            'title': title,
                                            'url': url,
                                            'source': source_elem.get_text().strip() if source_elem else 'Google News',
                                            'date': time_elem.get('datetime', '') if time_elem else '',
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

            async with session.get(url, headers=headers) as response:
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

                                if exclude_russian and self.is_russian_domain(url):
                                    continue

                                snippet_elem = result.find('a', class_='result__snippet')

                                if url and url.startswith('http'):
                                    articles.append({
                                        'title': title,
                                        'url': url,
                                        'source': 'DuckDuckGo',
                                        'description': snippet_elem.get_text().strip()[:150] + '...' if snippet_elem else '',
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

                yandex_results = await self.search_yandex_news_direct(f"{query} ЭПР")
                all_results.extend(yandex_results)
                logger.info(f"✅ Яндекс.Новости: {len(yandex_results)} статей")

                bing_ru_results = await self.search_bing_news_improved(f"{query} ЭПР", 'ru-RU')
                all_results.extend(bing_ru_results)
                logger.info(f"✅ Bing Россия: {len(bing_ru_results)} статей")

            if search_type in ["all", "international"]:
                logger.info(f"🌍 Поиск в международных источниках: {query}")

                translated_query = await self.translate_query(query)
                logger.info(f"🌍 Переведенный запрос: {translated_query}")

                google_results = await self.search_google_news_english(translated_query)
                all_results.extend(google_results)
                logger.info(f"✅ Google News: {len(google_results)} статей")

                bing_en_results = await self.search_bing_news_improved(translated_query, 'en-US', exclude_russian=True)
                all_results.extend(bing_en_results)
                logger.info(f"✅ Bing International: {len(bing_en_results)} статей")

                duckduckgo_results = await self.search_duckduckgo_improved(translated_query, exclude_russian=True)
                all_results.extend(duckduckgo_results)
                logger.info(f"✅ DuckDuckGo: {len(duckduckgo_results)} статей")

        except Exception as e:
            logger.error(f"❌ Ошибка в универсальном поиске: {e}")

        filtered_results = []
        for result in all_results:
            if result and result.get('url'):
                url = result['url'].lower()
                if any(search_domain in url for search_domain in [
                    'google.com/search',
                    'bing.com/search',
                    'yandex.ru/search',
                    'news.google.com',
                    'news.yandex.ru/yandsearch'
                ]):
                    continue
                
                if search_type == "international" and self.is_russian_domain(url):
                    continue
                    
                if url.startswith('http') and len(url) > 20:
                    filtered_results.append(result)

        seen_urls = set()
        unique_results = []
        for result in filtered_results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)

        self.set_cached_results(cache_key, unique_results[:10])

        logger.info(f"📊 Итоговые результаты: {len(unique_results)} статей")
        return unique_results[:10]

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
            "экспериментальный правовой режим новости"
        ]

        all_articles = []

        for query in today_queries:
            try:
                logger.info(f"📢 Поиск свежих новостей: {query}")

                yandex_results = await self.search_yandex_news_direct(query)
                bing_results = await self.search_bing_news_improved(query, 'ru-RU')

                all_articles.extend(yandex_results)
                all_articles.extend(bing_results)

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Ошибка при поиске свежих новостей: {e}")
                continue

        filtered_articles = []
        for article in all_articles:
            if article and article.get('url'):
                url = article['url'].lower()
                if not any(search_domain in url for search_domain in [
                    'google.com/search', 'bing.com/search', 'yandex.ru/search'
                ]) and url.startswith('http') and len(url) > 20:
                    filtered_articles.append(article)

        seen_urls = set()
        unique_articles = []
        for article in filtered_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        if len(unique_articles) < 4:
            logger.info("🔍 Дополнительный поиск свежих новостей...")
            backup_queries = ["ЭПР", "регуляторная песочница Россия"]
            for query in backup_queries:
                try:
                    backup_results = await self.universal_search(query, "all")
                    for article in backup_results:
                        if article['url'] not in seen_urls:
                            seen_urls.add(article['url'])
                            unique_articles.append(article)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Ошибка дополнительного поиска: {e}")

        final_articles = unique_articles[:8]
        self.set_cached_results(cache_key, final_articles)

        logger.info(f"✅ Найдено свежих новостей: {len(final_articles)}")
        return final_articles

    async def close(self):
        if self.session:
            await self.session.close()

news_searcher = ImprovedNewsSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌐 Универсальный поиск новостей об ЭПР\n\n"
        "🔍 Поиск новостей – российские и международные источники\n"
        "🌍 Международные источники – только зарубежные СМИ\n"
        "⚡ Свежие новости – актуальные статьи\n"
        "📊 Быстрый поиск – мгновенные результаты\n\n"
        "Просто напишите что ищете!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
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

@dp.message(lambda message: message.text == "🔍 Поиск новостей")
async def search_epr_news(message: types.Message):
    await message.answer("🔍 Напишите запрос для поиска новостей:")

@dp.message(lambda message: message.text == "🌍 Международные источники")
async def international_sources(message: types.Message):
    await message.answer("🌍 Напишите запрос для поиска в международных источниках:")

@dp.message(lambda message: message.text == "⚡ Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("⚡ Ищу самые свежие новости")

    try:
        articles = await news_searcher.get_fresh_news_today()

        if articles:
            response = "⚡ Самые свежие новости:\n\n"

            for i, article in enumerate(articles, 1):
                response += f"{i}. {article['title']}\n"
                response += f"   📰 {article['source']}\n"
                if article.get('date'):
                    formatted_date = format_date(article['date'])
                    if formatted_date:
                        response += f"   📅 {formatted_date}\n"
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

@dp.message(lambda message: message.text == "📊 Быстрый поиск")
async def quick_search(message: types.Message):
    await message.answer("📊 Напишите запрос для быстрого поиска по всем источникам:")

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()

    buttons = [
        "🔍 Поиск новостей",
        "🌍 Международные источники",
        "⚡ Свежие новости",
        "📊 Быстрый поиск"]
    if user_text.startswith('/') or user_text in buttons:
        return

    await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")

    try:
        if any(word in user_text.lower()
           for word in ['russia', 'russian', 'international']):
            search_type = "international"
            response_note = "🌍 Поиск только в международных источниках\n"
        else:
            search_type = "all"
            response_note = "🔍 Поиск по русским источникам\n"

        articles = await news_searcher.universal_search(user_text, search_type)

        if articles:
            russian_articles = [a for a in articles if a.get('language') == 'ru']
            english_articles = [a for a in articles if a.get('language') == 'en']

            response = f"🔍 Результаты поиска по '{user_text}':\n\n"

            if russian_articles and search_type != "international":
                response += "🇷🇺 Российские источники:\n\n"
                for i, article in enumerate(russian_articles[:4], 1):
                    response += f"{i}. {article['title']}\n"
                    response += f"   📰 {article['source']}\n"
                    if article.get('date'):
                        formatted_date = format_date(article['date'])
                        if formatted_date:
                            response += f"   📅 {formatted_date}\n"
                    response += f"   🔗 {article['url']}\n\n"

            if english_articles and search_type == "international":
                response += "🌍 Международные источники:\n\n"
                for i, article in enumerate(english_articles[:4], 1):
                    response += f"{i}. {article['title']}\n"
                    response += f"   📰 {article['source']}\n"
                    if article.get('date'):
                        formatted_date = format_date(article['date'])
                        if formatted_date:
                            response += f"   📅 {formatted_date}\n"
                    response += f"   🔗 {article['url']}\n\n"

            response += f"📊 Найдено статей: {len(articles)}"

        else:
            response = f"😔 По запросу '{user_text}' не найдено новостей.\n\n"
            response += "💡 Попробуйте изменить формулировку запроса."

        await message.answer(response)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        await message.answer(f"❌ Ошибка при поиске. Попробуйте другой запрос.")

async def main():
    logger.info("🚀 Запуск улучшенного поискового бота...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await news_searcher.close()

if __name__ == "__main__":
    asyncio.run(main())
