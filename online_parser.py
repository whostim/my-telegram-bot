import aiohttp
import asyncio
import ssl
import feedparser
import logging
from datetime import datetime
import urllib.parse

logger = logging.getLogger(__name__)

class OnlineNewsParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def search_news(self, query, max_results=10):
        results = []
        
        tasks = [
            self.search_google_news(query),
            self.search_yandex_news(query),
        ]
        
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in search_results:
            if isinstance(result, list):
                results.extend(result)
        
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return self.remove_duplicates(results)[:max_results]
    
    async def search_google_news(self, query):
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
                        
                        for entry in feed.entries[:5]:
                            published = self.parse_date(entry.get('published', ''))
                            results.append({
                                'title': entry.title,
                                'url': entry.link,
                                'source': f"Google News",
                                'description': entry.get('description', '')[:100] + '...',
                                'date': published.strftime("%Y-%m-%d %H:%M"),
                                'timestamp': published.timestamp()
                            })
        except Exception as e:
            logger.error(f"Google News error: {e}")
        
        return results
    
    async def search_yandex_news(self, query):
        results = []
        try:
            url = "https://news.yandex.ru/index.rss"
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:5]:
                            content_text = f"{entry.title} {entry.get('description', '')}".lower()
                            if any(keyword in content_text for keyword in ['песочница', 'эпр', 'регулятор']):
                                published = self.parse_date(entry.get('published', ''))
                                results.append({
                                    'title': entry.title,
                                    'url': entry.link,
                                    'source': 'Яндекс.Новости',
                                    'description': entry.get('description', '')[:100] + '...',
                                    'date': published.strftime("%Y-%m-%d %H:%M"),
                                    'timestamp': published.timestamp()
                                })
        except Exception as e:
            logger.error(f"Yandex News error: {e}")
        
        return results
    
    def parse_date(self, date_string):
        if not date_string:
            return datetime.now()
        try:
            return feedparser._parse_date(date_string)
        except:
            return datetime.now()
    
    def remove_duplicates(self, results):
        seen = set()
        unique = []
        for item in results:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique

async def test_parser():
    parser = OnlineNewsParser()
    print("🔍 Тестируем парсер...")
    results = await parser.search_news("песочница")
    print(f"Найдено: {len(results)}")
    for i, item in enumerate(results[:2], 1):
        print(f"{i}. {item['title']}")

if __name__ == "__main__":
    asyncio.run(test_parser())
