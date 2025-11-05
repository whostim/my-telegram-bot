import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

class RealNewsParser:
    def __init__(self):
        self.session = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    async def search_news(self, query, hours_back=24):
        """Реальный поиск новостей"""
        results = []
        
        # Поиск в Google News
        google_results = await self.search_google_news(query)
        results.extend(google_results)
        
        # Поиск в Яндекс.Новостях
        yandex_results = await self.search_yandex_news(query)
        results.extend(yandex_results)
        
        # Поиск в RSS лентах
        rss_results = await self.search_rss_feeds(query)
        results.extend(rss_results)
        
        return self.remove_duplicates(results)
    
    async def search_google_news(self, query):
        """Поиск в Google News"""
        results = []
        try:
            url = f"https://news.google.com/rss/search?q={query}+Россия&hl=ru&gl=RU&ceid=RU:ru"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': self.user_agent}) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:10]:
                            results.append({
                                'title': entry.title,
                                'url': entry.link,
                                'source': f"Google News: {entry.get('source', {}).get('title', '')}",
                                'description': entry.get('description', ''),
                                'date': entry.get('published', ''),
                                'real': True
                            })
        except Exception as e:
            logger.error(f"Google News error: {e}")
        
        return results
    
    async def search_yandex_news(self, query):
        """Поиск в Яндекс.Новостях"""
        results = []
        try:
            url = f"https://newssearch.yandex.ru/news/search"
            params = {
                'text': f'{query} Россия',
                'rpt': 'nnews2',
                'grhow': 'clutzer'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers={'User-Agent': self.user_agent}) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Парсим результаты (это упрощенный парсинг)
                        news_items = soup.find_all('div', class_=re.compile('news-item|news-story'))
                        
                        for item in news_items[:10]:
                            title_elem = item.find('h2') or item.find('a')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = title_elem.get('href')
                                if title and link:
                                    results.append({
                                        'title': title,
                                        'url': link if link.startswith('http') else f'https:{link}',
                                        'source': 'Яндекс.Новости',
                                        'description': '',
                                        'date': datetime.now().strftime("%Y-%m-%d"),
                                        'real': True
                                    })
        except Exception as e:
            logger.error(f"Yandex News error: {e}")
        
        return results
    
    async def search_rss_feeds(self, query):
        """Поиск в RSS лентах"""
        results = []
        
        rss_feeds = [
            'https://lenta.ru/rss/news',
            'https://www.vedomosti.ru/rss/news',
            'https://www.kommersant.ru/RSS/news.xml',
            'https://ria.ru/export/rss2/index.xml',
            'https://tass.ru/rss/v2.xml',
            'https://www.rbc.ru/rssfeed/news.rss'
        ]
        
        async with aiohttp.ClientSession() as session:
            for rss_url in rss_feeds:
                try:
                    async with session.get(rss_url, headers={'User-Agent': self.user_agent}) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:
                                content_text = f"{entry.title} {entry.get('description', '')}".lower()
                                if any(keyword in content_text for keyword in ['песочниц', 'регулятор', 'эпр', 'эксперимент']):
                                    results.append({
                                        'title': entry.title,
                                        'url': entry.link,
                                        'source': f"RSS: {rss_url.split('/')[2]}",
                                        'description': entry.get('description', ''),
                                        'date': entry.get('published', ''),
                                        'real': True
                                    })
                except Exception as e:
                    logger.warning(f"RSS error {rss_url}: {e}")
        
        return results
    
    def remove_duplicates(self, results):
        """Удаление дубликатов"""
        seen = set()
        unique = []
        for item in results:
            identifier = item['url']
            if identifier not in seen:
                seen.add(identifier)
                unique.append(item)
        return unique

# Тестируем парсер
async def test_parser():
    parser = RealNewsParser()
    print("🔍 Тестируем реальный поиск...")
    
    results = await parser.search_news("песочница")
    print(f"Найдено результатов: {len(results)}")
    
    for i, item in enumerate(results[:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Source: {item['source']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_parser())
