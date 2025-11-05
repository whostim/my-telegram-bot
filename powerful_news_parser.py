import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import feedparser
import re
import json
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
import time
from config import Config
import logging

logger = logging.getLogger(__name__)

class PowerfulNewsParser:
    def __init__(self):
        self.config = Config()
        self.telegram_client = None
        self.setup_telegram()
    
    def setup_telegram(self):
        """Настройка Telegram клиента"""
        if self.config.API_ID and self.config.API_HASH:
            try:
                self.telegram_client = TelegramClient(
                    'news_session', 
                    self.config.API_ID, 
                    self.config.API_HASH
                )
                logger.info("Telegram client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram client: {e}")
    
    async def search_all_sources(self, query, hours_back=24):
        """Поиск по всем источникам за указанное количество часов"""
        results = []
        
        # Поиск в Telegram каналах
        telegram_results = await self.search_telegram_channels(query, hours_back)
        results.extend(telegram_results)
        
        # Поиск в Google News
        google_results = await self.search_google_news_realtime(query)
        results.extend(google_results)
        
        # Поиск в Яндекс.Новостях
        yandex_results = await self.search_yandex_realtime(query)
        results.extend(yandex_results)
        
        # Поиск в RSS лентах
        rss_results = await self.search_rss_realtime(query, hours_back)
        results.extend(rss_results)
        
        # Поиск в социальных сетях и форумах
        social_results = await self.search_social_media(query)
        results.extend(social_results)
        
        # Сортируем по дате (сначала самые свежие)
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return self.remove_duplicates(results)[:20]
    
    async def search_telegram_channels(self, query, hours_back=24):
        """Поиск в Telegram каналах"""
        results = []
        
        if not self.telegram_client:
            return results
        
        try:
            await self.telegram_client.start()
            
            since_date = datetime.now() - timedelta(hours=hours_back)
            
            for channel in self.config.TELEGRAM_CHANNELS:
                try:
                    # Пытаемся получить entity канала
                    entity = await self.telegram_client.get_entity(channel)
                    
                    # Ищем сообщения по ключевым словам
                    async for message in self.telegram_client.iter_messages(
                        entity, 
                        limit=50,
                        offset_date=since_date,
                        search=query
                    ):
                        if message.text:
                            content = message.text.lower()
                            if any(keyword in content for keyword in self.config.KEYWORDS + [query.lower()]):
                                results.append({
                                    'title': message.text[:100] + '...' if len(message.text) > 100 else message.text,
                                    'url': f"https://t.me/{channel}/{message.id}",
                                    'source': f"Telegram: {channel}",
                                    'description': message.text[:200] + '...' if len(message.text) > 200 else message.text,
                                    'keywords': [query],
                                    'date': message.date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': message.date.timestamp()
                                })
                except Exception as e:
                    logger.warning(f"Could not access channel {channel}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Telegram search error: {e}")
        finally:
            if self.telegram_client and self.telegram_client.is_connected():
                await self.telegram_client.disconnect()
        
        return results
    
    async def search_google_news_realtime(self, query):
        """Поиск в Google News в реальном времени"""
        results = []
        try:
            # Используем Google News RSS с поиском
            search_url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}+Россия&hl=ru&gl=RU&ceid=RU:ru"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:15]:
                            try:
                                pub_date = date_parser.parse(entry.published)
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Google News: ' + entry.get('source', {}).get('title', 'Unknown'),
                                    'description': entry.get('description', '')[:200] + '...',
                                    'keywords': [query],
                                    'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': pub_date.timestamp()
                                })
                            except:
                                continue
        except Exception as e:
            logger.error(f"Google News search error: {e}")
        
        return results
    
    async def search_yandex_realtime(self, query):
        """Поиск в Яндекс.Новостях"""
        results = []
        try:
            url = "https://yandex.ru/news/rss/search"
            params = {
                'text': f'{query} Россия',
                'from': 'index'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:10]:
                            try:
                                pub_date = date_parser.parse(entry.published)
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Яндекс.Новости',
                                    'description': entry.get('description', '')[:200] + '...',
                                    'keywords': [query],
                                    'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': pub_date.timestamp()
                                })
                            except:
                                continue
        except Exception as e:
            logger.error(f"Yandex News search error: {e}")
        
        return results
    
    async def search_rss_realtime(self, query, hours_back=24):
        """Поиск в RSS лентах в реальном времени"""
        results = []
        
        async with aiohttp.ClientSession() as session:
            for rss_url in self.config.RSS_SOURCES:
                try:
                    async with session.get(rss_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:10]:
                                try:
                                    pub_date = date_parser.parse(entry.published)
                                    # Проверяем что новость свежая
                                    if datetime.now() - pub_date < timedelta(hours=hours_back):
                                        content_text = f"{entry.title} {entry.get('description', '')}".lower()
                                        if any(keyword in content_text for keyword in self.config.KEYWORDS + [query.lower()]):
                                            results.append({
                                                'title': entry.title,
                                                'url': entry.link,
                                                'source': f"RSS: {rss_url.split('/')[2]}",
                                                'description': entry.get('description', '')[:150] + '...',
                                                'keywords': [query],
                                                'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                                'timestamp': pub_date.timestamp()
                                            })
                                except:
                                    continue
                except Exception as e:
                    logger.warning(f"RSS feed {rss_url} error: {e}")
        
        return results
    
    async def search_social_media(self, query):
        """Поиск в социальных сетях и форумах"""
        results = []
        
        # Поиск в VK (через неофициальные методы)
        try:
            vk_url = f"https://api.vk.com/method/newsfeed.search"
            params = {
                'q': f'{query} регуляторная песочница',
                'count': 10,
                'v': '5.131'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(vk_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'response' in data:
                            for item in data['response'].get('items', [])[:5]:
                                results.append({
                                    'title': f"VK: {item.get('text', '')[:50]}...",
                                    'url': f"https://vk.com/wall{item.get('owner_id')}_{item.get('id')}",
                                    'source': 'VKontakte',
                                    'description': item.get('text', '')[:100] + '...',
                                    'keywords': [query],
                                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': datetime.now().timestamp()
                                })
        except Exception as e:
            logger.warning(f"VK search error: {e}")
        
        return results
    
    def remove_duplicates(self, results):
        """Удаление дубликатов по URL и заголовку"""
        seen_urls = set()
        seen_titles = set()
        unique_results = []
        
        for result in results:
            url = result['url']
            title = result['title'][:50]  # Берем первую часть заголовка для сравнения
            
            if url not in seen_urls and title not in seen_titles:
                seen_urls.add(url)
                seen_titles.add(title)
                unique_results.append(result)
        
        return unique_results
    
    async def get_trending_news(self):
        """Получение трендовых новостей по теме"""
        trending_results = []
        
        # Ищем по всем ключевым словам
        for keyword in self.config.KEYWORDS[:3]:  # Берем топ-3 ключевых слова
            try:
                news = await self.search_all_sources(keyword, hours_back=6)  # Только за последние 6 часов
                trending_results.extend(news)
                
                # Небольшая задержка чтобы не перегружать
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting trending for {keyword}: {e}")
        
        # Сортируем по времени и убираем дубликаты
        trending_results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return self.remove_duplicates(trending_results)[:10]

# Упрощенная версия без Telegram (если нет API keys)
class SimplePowerfulParser:
    def __init__(self):
        self.config = Config()
    
    async def search_all_sources(self, query, hours_back=24):
        """Упрощенный поиск без Telegram"""
        results = []
        
        # Google News
        google_results = await self.search_google_news_realtime(query)
        results.extend(google_results)
        
        # Яндекс.Новости
        yandex_results = await self.search_yandex_realtime(query)
        results.extend(yandex_results)
        
        # RSS ленты
        rss_results = await self.search_rss_realtime(query, hours_back)
        results.extend(rss_results)
        
        # Сортируем по дате
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return self.remove_duplicates(results)[:15]
    
    async def search_google_news_realtime(self, query):
        """Поиск в Google News"""
        results = []
        try:
            search_url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}+Россия&hl=ru&gl=RU&ceid=RU:ru"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:10]:
                            try:
                                pub_date = date_parser.parse(entry.published)
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Google News',
                                    'description': entry.get('description', '')[:200] + '...',
                                    'keywords': [query],
                                    'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': pub_date.timestamp()
                                })
                            except:
                                continue
        except Exception as e:
            logger.error(f"Google News error: {e}")
        
        return results
    
    async def search_yandex_realtime(self, query):
        """Поиск в Яндекс.Новостях"""
        results = []
        try:
            url = "https://yandex.ru/news/rss/search"
            params = {'text': f'{query} Россия'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:8]:
                            try:
                                pub_date = date_parser.parse(entry.published)
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Яндекс.Новости',
                                    'description': entry.get('description', '')[:200] + '...',
                                    'keywords': [query],
                                    'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': pub_date.timestamp()
                                })
                            except:
                                continue
        except Exception as e:
            logger.error(f"Yandex News error: {e}")
        
        return results
    
    async def search_rss_realtime(self, query, hours_back=24):
        """Поиск в RSS лентах"""
        results = []
        
        rss_sources = [
            'https://lenta.ru/rss/news',
            'https://www.vedomosti.ru/rss/news',
            'https://www.kommersant.ru/RSS/news.xml',
            'https://ria.ru/export/rss2/index.xml',
            'https://tass.ru/rss/v2.xml',
            'https://www.rbc.ru/rssfeed/news.rss',
            'https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru'
        ]
        
        async with aiohttp.ClientSession() as session:
            for rss_url in rss_sources:
                try:
                    async with session.get(rss_url, timeout=8) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:
                                try:
                                    pub_date = date_parser.parse(entry.published)
                                    if datetime.now() - pub_date < timedelta(hours=hours_back):
                                        content_text = f"{entry.title} {entry.get('description', '')}".lower()
                                        if any(keyword in content_text for keyword in self.config.KEYWORDS + [query.lower()]):
                                            results.append({
                                                'title': entry.title,
                                                'url': entry.link,
                                                'source': f"RSS: {rss_url.split('/')[2]}",
                                                'description': entry.get('description', '')[:150] + '...',
                                                'keywords': [query],
                                                'date': pub_date.strftime("%Y-%m-%d %H:%M"),
                                                'timestamp': pub_date.timestamp()
                                            })
                                except:
                                    continue
                except Exception as e:
                    continue
        
        return results
    
    def remove_duplicates(self, results):
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        return unique_results
    
    async def get_trending_news(self):
        """Трендовые новости"""
        trending = []
        for keyword in ['песочница', 'ЭПР', 'регуляторный']:
            news = await self.search_all_sources(keyword, hours_back=6)
            trending.extend(news)
            await asyncio.sleep(0.5)
        
        trending.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return self.remove_duplicates(trending)[:8]
