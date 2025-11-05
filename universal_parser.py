import aiohttp
import asyncio
import ssl
import feedparser
from datetime import datetime, timedelta
import urllib.parse
import logging
from telethon import TelegramClient
from telethon.tl.types import Message
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class UniversalParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Telegram клиент
        self.tg_client = None
        self.setup_telegram()
    
    def setup_telegram(self):
        """Настройка Telegram клиента"""
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        
        if api_id and api_hash:
            try:
                self.tg_client = TelegramClient('tg_session', api_id, api_hash)
                logger.info("Telegram client initialized")
            except Exception as e:
                logger.error(f"Telegram client error: {e}")
    
    async def search_all_sources(self, query, max_results=15):
        """Поиск по всем источникам"""
        results = []
        
        # Запускаем поиск параллельно
        tasks = [
            self.search_google_news(query),
            self.search_yandex_news(query),
            self.search_telegram_channels(query),
            self.search_rss_feeds(query),
            self.search_duckduckgo(query)
        ]
        
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in search_results:
            if isinstance(result, list):
                results.extend(result)
        
        # Сортируем по дате (сначала новые)
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return self.remove_duplicates(results)[:max_results]
    
    async def search_google_news(self, query):
        """Поиск в Google News"""
        results = []
        try:
            encoded_query = urllib.parse.quote(f"{query} Россия")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ru&gl=RU&ceid=RU:ru"
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:8]:
                            published = self.parse_date(entry.get('published', ''))
                            results.append({
                                'title': entry.title,
                                'url': entry.link,
                                'source': f"Google News: {entry.get('source', {}).get('title', '')}",
                                'description': entry.get('description', '')[:150] + '...',
                                'date': published.strftime("%Y-%m-%d %H:%M"),
                                'timestamp': published.timestamp(),
                                'type': 'news'
                            })
        except Exception as e:
            logger.error(f"Google News error: {e}")
        
        return results
    
    async def search_yandex_news(self, query):
        """Поиск в Яндекс.Новостях"""
        results = []
        try:
            url = "https://news.yandex.ru/index.rss"
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:6]:
                            content_text = f"{entry.title} {entry.get('description', '')}".lower()
                            if any(keyword in content_text for keyword in ['эпр', 'песочница', 'регулятор']):
                                published = self.parse_date(entry.get('published', ''))
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Яндекс.Новости',
                                    'description': entry.get('description', '')[:150] + '...',
                                    'date': published.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': published.timestamp(),
                                    'type': 'news'
                                })
        except Exception as e:
            logger.error(f"Yandex News error: {e}")
        
        return results
    
    async def search_telegram_channels(self, query):
        """Поиск в Telegram каналах"""
        results = []
        
        if not self.tg_client:
            return results
        
        try:
            await self.tg_client.start()
            
            # Популярные каналы про технологии и инновации
            channels = [
                'vcru',           # VC.RU
                'rbcdaily',       # РБК
                'vedomosti',      # Ведомости
                'tass_agency',    # ТАСС
                'rian_ru',        # РИА Новости
                'rt_russian',     # Russia Today
                'meduzalive',     # Медуза
                'lentach',        # Лентач
                'digital_gov_ru', # Digital.gov.ru
            ]
            
            since_date = datetime.now() - timedelta(hours=24)
            
            for channel in channels:
                try:
                    entity = await self.tg_client.get_entity(channel)
                    
                    async for message in self.tg_client.iter_messages(
                        entity, 
                        limit=5,
                        offset_date=since_date,
                        search=query
                    ):
                        if message.text:
                            content = message.text.lower()
                            if query.lower() in content:
                                results.append({
                                    'title': message.text[:100] + '...' if len(message.text) > 100 else message.text,
                                    'url': f"https://t.me/{channel}/{message.id}",
                                    'source': f"Telegram: {channel}",
                                    'description': message.text[:200] + '...' if len(message.text) > 200 else message.text,
                                    'date': message.date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': message.date.timestamp(),
                                    'type': 'telegram'
                                })
                except Exception as e:
                    logger.warning(f"Channel {channel} error: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Telegram search error: {e}")
        finally:
            if self.tg_client and self.tg_client.is_connected():
                await self.tg_client.disconnect()
        
        return results
    
    async def search_rss_feeds(self, query):
        """Поиск в RSS лентах"""
        results = []
        
        rss_feeds = [
            'https://lenta.ru/rss/news',
            'https://www.rbc.ru/rssfeed/news.rss',
            'https://www.vedomosti.ru/rss/news',
        ]
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            for rss_url in rss_feeds:
                try:
                    async with session.get(rss_url, timeout=8) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:4]:
                                content_text = f"{entry.title} {entry.get('description', '')}".lower()
                                if query.lower() in content_text:
                                    published = self.parse_date(entry.get('published', ''))
                                    results.append({
                                        'title': entry.title,
                                        'url': entry.link,
                                        'source': f"RSS: {rss_url.split('/')[2]}",
                                        'description': entry.get('description', '')[:150] + '...',
                                        'date': published.strftime("%Y-%m-%d %H:%M"),
                                        'timestamp': published.timestamp(),
                                        'type': 'news'
                                    })
                except Exception as e:
                    logger.warning(f"RSS error {rss_url}: {e}")
                    continue
        
        return results
    
    async def search_duckduckgo(self, query):
        """Поиск через DuckDuckGo"""
        results = []
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                'q': f'{query} Россия новости',
                'format': 'json',
                'no_html': '1'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for topic in data.get('RelatedTopics', [])[:3]:
                            if 'FirstURL' in topic and 'Text' in topic:
                                results.append({
                                    'title': topic['Text'],
                                    'url': topic['FirstURL'],
                                    'source': 'DuckDuckGo',
                                    'description': 'Результат поиска',
                                    'date': datetime.now().strftime("%Y-%m-%d"),
                                    'timestamp': datetime.now().timestamp(),
                                    'type': 'search'
                                })
        except Exception as e:
            logger.warning(f"DuckDuckGo error: {e}")
        
        return results
    
    def parse_date(self, date_string):
        """Парсинг даты"""
        if not date_string:
            return datetime.now()
        try:
            return feedparser._parse_date(date_string)
        except:
            return datetime.now()
    
    def remove_duplicates(self, results):
        """Удаление дубликатов"""
        seen = set()
        unique = []
        for item in results:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique

# Тестируем парсер
async def test_universal_parser():
    parser = UniversalParser()
    print("🔍 Тестируем универсальный парсер...")
    
    results = await parser.search_all_sources("ЭПР")
    print(f"Найдено результатов: {len(results)}")
    
    for i, item in enumerate(results[:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Source: {item['source']}")
        print(f"   Type: {item['type']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_universal_parser())
