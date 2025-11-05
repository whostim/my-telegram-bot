import aiohttp
import asyncio
import ssl
import certifi
import feedparser
import logging
from datetime import datetime
import urllib.parse

logger = logging.getLogger(__name__)

class FixedNewsParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
    async def search_news(self, query):
        """Поиск новостей с обходом SSL проблем"""
        results = []
        
        # Поиск в Google News (обычно работает без проблем)
        google_results = await self.search_google_safe(query)
        results.extend(google_results)
        
        # Поиск через NewsAPI (бесплатный вариант)
        newsapi_results = await self.search_newsapi(query)
        results.extend(newsapi_results)
        
        # Поиск через RSS с обходом SSL
        rss_results = await self.search_rss_safe(query)
        results.extend(rss_results)
        
        return self.remove_duplicates(results)
    
    async def search_google_safe(self, query):
        """Безопасный поиск через Google News"""
        results = []
        try:
            # Используем HTTPS без сложных SSL проверок
            search_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+Россия&hl=ru&gl=RU&ceid=RU:ru"
            
            # Создаем SSL контекст который игнорирует ошибки сертификатов
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(search_url, headers={'User-Agent': self.user_agent}) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:8]:
                            results.append({
                                'title': entry.title,
                                'url': entry.link,
                                'source': f"Google News: {entry.get('source', {}).get('title', '')}",
                                'description': entry.get('description', '')[:150] + '...' if entry.get('description') else 'Описание отсутствует',
                                'date': entry.get('published', datetime.now().strftime("%Y-%m-%d")),
                                'real': True
                            })
        except Exception as e:
            logger.error(f"Google News error: {e}")
        
        return results
    
    async def search_newsapi(self, query):
        """Поиск через NewsAPI (нужен API ключ)"""
        results = []
        try:
            # NewsAPI требует регистрации, но есть бесплатный план
            api_key = "your_newsapi_key_here"  # Нужно получить на newsapi.org
            if api_key == "your_newsapi_key_here":
                return results  # Пропускаем если ключ не установлен
                
            url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(query)}&language=ru&sortBy=publishedAt&apiKey={api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        for article in data.get('articles', [])[:5]:
                            results.append({
                                'title': article['title'],
                                'url': article['url'],
                                'source': f"NewsAPI: {article['source']['name']}",
                                'description': article.get('description', '')[:150] + '...',
                                'date': article['publishedAt'][:10],
                                'real': True
                            })
        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")
        
        return results
    
    async def search_rss_safe(self, query):
        """Безопасный поиск по RSS с обходом проблемных сайтов"""
        results = []
        
        # Используем только надежные RSS источники
        safe_rss_feeds = [
            'https://rss.news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru',  # Google News RSS
            'https://feeds.bbci.co.uk/russian/rss.xml',  # BBC Russian
        ]
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            for rss_url in safe_rss_feeds:
                try:
                    async with session.get(rss_url, headers={'User-Agent': self.user_agent}, timeout=8) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:
                                content_text = f"{entry.title} {entry.get('description', '')}".lower()
                                if any(keyword in content_text for keyword in ['россия', 'москва', 'правительство', 'закон', 'регулятор']):
                                    results.append({
                                        'title': entry.title,
                                        'url': entry.link,
                                        'source': f"RSS: {rss_url.split('/')[2]}",
                                        'description': entry.get('description', '')[:100] + '...',
                                        'date': entry.get('published', ''),
                                        'real': True
                                    })
                except Exception as e:
                    logger.warning(f"RSS error {rss_url}: {e}")
                    continue
        
        return results
    
    def remove_duplicates(self, results):
        seen = set()
        unique = []
        for item in results:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique.append(item)
        return unique

# Тест парсера
async def test_fixed_parser():
    parser = FixedNewsParser()
    print("🔍 Тестируем исправленный парсер...")
    
    results = await parser.search_news("песочница регуляторная")
    print(f"Найдено результатов: {len(results)}")
    
    for i, item in enumerate(results[:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Source: {item['source']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_fixed_parser())
