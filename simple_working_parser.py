import aiohttp
import asyncio
import logging
from datetime import datetime
import urllib.parse

logger = logging.getLogger(__name__)

class WorkingParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    
    async def search_news(self, query, max_results=8):
        """Упрощенный поиск, который всегда работает"""
        results = []
        
        # Всегда возвращаем результаты с поисковыми ссылками
        search_engines = [
            {
                'name': 'Google News',
                'url': f'https://news.google.com/search?q={urllib.parse.quote(query + " Россия")}&hl=ru&gl=RU&ceid=RU:ru'
            },
            {
                'name': 'Яндекс.Новости', 
                'url': f'https://yandex.ru/news/search?text={urllib.parse.quote(query + " ЭПР")}'
            },
            {
                'name': 'Telegram Search',
                'url': f'https://t.me/search?q={urllib.parse.quote(query)}'
            },
            {
                'name': 'DuckDuckGo',
                'url': f'https://duckduckgo.com/?q={urllib.parse.quote(query + " Россия новости")}&ia=news'
            }
        ]
        
        # Добавляем официальные источники
        official_sources = [
            {
                'title': 'Digital.gov.ru - Регуляторные песочницы',
                'url': 'https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/',
                'source': 'Официальный сайт',
                'description': 'Официальная информация о регуляторных песочницах в РФ'
            },
            {
                'title': 'Минэкономразвития - Регулируемый сэндбокс',
                'url': 'https://www.economy.gov.ru/material/directions/reguliruemyy_sandboks/',
                'source': 'Официальный сайт', 
                'description': 'Информация о регулируемых сэндбоксах для бизнеса'
            },
            {
                'title': 'ЦБ РФ - Финтех и инновации',
                'url': 'https://www.cbr.ru/fintech/',
                'source': 'Официальный сайт',
                'description': 'Информация о финтехе и регуляторных инновациях'
            }
        ]
        
        # Создаем результаты поиска
        for engine in search_engines:
            results.append({
                'title': f'🔍 {engine["name"]} - {query}',
                'url': engine['url'],
                'source': engine['name'],
                'description': f'Нажмите для поиска в {engine["name"]}',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp(),
                'type': 'search_engine'
            })
        
        # Добавляем официальные источники
        for source in official_sources:
            if query.lower() in source['title'].lower() or any(keyword in query.lower() for keyword in ['эпр', 'песочница', 'регулятор']):
                results.append({
                    'title': source['title'],
                    'url': source['url'],
                    'source': source['source'],
                    'description': source['description'],
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'timestamp': datetime.now().timestamp(),
                    'type': 'official'
                })
        
        return results[:max_results]
    
    async def test_connection(self):
        """Проверка доступности внешних ресурсов"""
        test_urls = [
            'https://www.google.com',
            'https://yandex.ru',
            'https://telegram.org'
        ]
        
        available = []
        async with aiohttp.ClientSession() as session:
            for url in test_urls:
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            available.append(url)
                except:
                    pass
        
        return available

# Тестируем парсер
async def test_working_parser():
    parser = WorkingParser()
    print("🔍 Тестируем рабочий парсер...")
    
    # Проверяем доступность
    available = await parser.test_connection()
    print(f"✅ Доступные ресурсы: {len(available)}")
    for resource in available:
        print(f"   - {resource}")
    
    # Тестируем поиск
    results = await parser.search_news("ЭПР")
    print(f"📊 Создано результатов: {len(results)}")
    
    for i, item in enumerate(results[:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Source: {item['source']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_working_parser())
