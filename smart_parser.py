import aiohttp
import asyncio
import logging
import json
from datetime import datetime
import urllib.parse

logger = logging.getLogger(__name__)

class SmartNewsParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    
    async def search_news(self, query, max_results=8):
        """Умный поиск новостей с разными методами"""
        results = []
        
        # Пробуем разные методы поиска
        methods = [
            self.search_duckduckgo(query),
            self.search_bing_news(query),
            self.search_newsapi_public(query),
        ]
        
        # Запускаем все методы
        search_results = await asyncio.gather(*methods, return_exceptions=True)
        
        for result in search_results:
            if isinstance(result, list):
                results.extend(result)
        
        # Если ничего не найдено, возвращаем демо-данные
        if not results:
            results = self.get_demo_news(query)
        
        return results[:max_results]
    
    async def search_duckduckgo(self, query):
        """Поиск через DuckDuckGo (более либеральный к запросам)"""
        results = []
        try:
            # DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': f'{query} Россия новости',
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Извлекаем связанные темы
                        for topic in data.get('RelatedTopics', [])[:5]:
                            if 'FirstURL' in topic and 'Text' in topic:
                                results.append({
                                    'title': topic['Text'],
                                    'url': topic['FirstURL'],
                                    'source': 'DuckDuckGo',
                                    'description': 'Поисковая выдача',
                                    'date': datetime.now().strftime("%Y-%m-%d"),
                                    'timestamp': datetime.now().timestamp()
                                })
        except Exception as e:
            logger.warning(f"DuckDuckGo error: {e}")
        
        return results
    
    async def search_bing_news(self, query):
        """Поиск через Bing News RSS"""
        results = []
        try:
            encoded_query = urllib.parse.quote(f"{query} site:ru")
            url = f"https://www.bing.com/news/search?q={encoded_query}&format=rss"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': self.user_agent}, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Простой парсинг RSS
                        if '<item>' in content:
                            import re
                            items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
                            
                            for item in items[:5]:
                                title_match = re.search(r'<title>(.*?)</title>', item)
                                link_match = re.search(r'<link>(.*?)</link>', item)
                                desc_match = re.search(r'<description>(.*?)</description>', item)
                                
                                if title_match and link_match:
                                    results.append({
                                        'title': title_match.group(1),
                                        'url': link_match.group(1),
                                        'source': 'Bing News',
                                        'description': desc_match.group(1) if desc_match else 'Новость из поиска',
                                        'date': datetime.now().strftime("%Y-%m-%d"),
                                        'timestamp': datetime.now().timestamp()
                                    })
        except Exception as e:
            logger.warning(f"Bing News error: {e}")
        
        return results
    
    async def search_newsapi_public(self, query):
        """Поиск через публичные NewsAPI endpoints"""
        results = []
        try:
            # Публичный endpoint (может быть ограничен)
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'{query} Russia',
                'language': 'ru',
                'sortBy': 'publishedAt',
                'pageSize': 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        for article in data.get('articles', []):
                            results.append({
                                'title': article['title'],
                                'url': article['url'],
                                'source': f"NewsAPI: {article['source']['name']}",
                                'description': article.get('description', '')[:100] + '...',
                                'date': datetime.now().strftime("%Y-%m-%d"),
                                'timestamp': datetime.now().timestamp()
                            })
        except Exception as e:
            logger.warning(f"NewsAPI public error: {e}")
        
        return results
    
    def get_demo_news(self, query):
        """Демо-новости когда реальные недоступны"""
        demo_news = [
            {
                'title': f'🔍 Результаты поиска по запросу: {query}',
                'url': f'https://www.google.com/search?q={urllib.parse.quote(query + " Россия новости")}',
                'source': 'Поисковая система',
                'description': 'Нажмите для просмотра результатов поиска в Google',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': f'📰 Новости об ЭПР и регуляторных песочницах',
                'url': 'https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/',
                'source': 'Digital.gov.ru',
                'description': 'Официальная информация о регуляторных песочницах в РФ',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': f'💡 Экспериментальные правовые режимы в России',
                'url': 'https://www.economy.gov.ru/material/directions/reguliruemyy_sandboks/',
                'source': 'Минэкономразвития',
                'description': 'Информация о регулируемых сэндбоксах для бизнеса',
                'date': datetime.now().strftime("%Y-%m-%d"),
                'timestamp': datetime.now().timestamp()
            }
        ]
        return demo_news

# Тестируем парсер
async def test_smart_parser():
    parser = SmartNewsParser()
    print("🔍 Тестируем умный парсер...")
    
    results = await parser.search_news("регуляторная песочница")
    print(f"Найдено результатов: {len(results)}")
    
    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Source: {item['source']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_smart_parser())
