import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import re
from datetime import datetime, timedelta
from config import Config

class AdvancedNewsParser:
    def __init__(self):
        self.config = Config()
        self.session = None
    
    async def search_all_sources(self, query):
        """Поиск по всем источникам"""
        results = []
        
        # Поиск в Яндекс.Новости
        yandex_results = await self.search_yandex_news(query)
        results.extend(yandex_results)
        
        # Поиск в Google News
        google_results = await self.search_google_news(query)
        results.extend(google_results)
        
        # Поиск по RSS лентам
        rss_results = await self.search_rss_feeds(query)
        results.extend(rss_results)
        
        # Поиск на официальных сайтах
        website_results = await self.search_websites(query)
        results.extend(website_results)
        
        # Убираем дубликаты
        unique_results = self.remove_duplicates(results)
        
        return unique_results[:15]  # Возвращаем до 15 результатов
    
    async def search_yandex_news(self, query):
        """Поиск через Яндекс.Новости"""
        results = []
        try:
            url = f"https://newssearch.yandex.ru/news/search"
            params = {
                'text': f'{query} Россия',
                'rpt': 'nnews2',
                'grhow': 'clutzer',
                'from': 'serp'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Парсим результаты (это упрощенный парсинг)
                        news_items = soup.find_all('div', class_='news-story')[:5]
                        
                        for item in news_items:
                            title_elem = item.find('h2') or item.find('a')
                            if title_elem:
                                title = title_elem.get_text().strip()
                                link = title_elem.get('href') if title_elem.name == 'a' else None
                                
                                if title and link:
                                    results.append({
                                        'title': title,
                                        'url': link if link.startswith('http') else f'https:{link}',
                                        'source': 'Яндекс.Новости',
                                        'description': 'Новость из Яндекс.Новостей',
                                        'keywords': [query],
                                        'date': 'Сегодня'
                                    })
        except Exception as e:
            print(f"Ошибка поиска в Яндекс: {e}")
        
        return results
    
    async def search_google_news(self, query):
        """Поиск через Google News"""
        results = []
        try:
            search_query = f"{query} Россия регуляторная песочница ЭПР"
            encoded_query = requests.utils.quote(search_query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ru&gl=RU&ceid=RU:ru"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:10]:
                            results.append({
                                'title': entry.title,
                                'url': entry.link,
                                'source': 'Google News: ' + entry.get('source', {}).get('title', ''),
                                'description': entry.get('description', '')[:200] + '...',
                                'keywords': [query],
                                'date': entry.get('published', 'Недавно')
                            })
        except Exception as e:
            print(f"Ошибка поиска в Google News: {e}")
        
        return results
    
    async def search_rss_feeds(self, query):
        """Поиск в RSS лентах российских СМИ"""
        results = []
        
        rss_sources = [
            'https://lenta.ru/rss/news',
            'https://www.vedomosti.ru/rss/news',
            'https://www.kommersant.ru/RSS/news.xml',
            'https://ria.ru/export/rss2/index.xml',
            'https://tass.ru/rss/v2.xml',
            'https://www.interfax.ru/rss.asp',
            'https://rg.ru/inc/rss/news.xml',
        ]
        
        async with aiohttp.ClientSession() as session:
            for rss_url in rss_sources:
                try:
                    async with session.get(rss_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:
                                title = entry.get('title', '')
                                description = entry.get('description', '')
                                content_text = f"{title} {description}".lower()
                                
                                # Проверяем релевантность
                                if any(keyword in content_text for keyword in 
                                      ['песочниц', 'регуляторн', 'эпр', 'экспериментальн', 'правов']):
                                    results.append({
                                        'title': title,
                                        'url': entry.link,
                                        'source': 'RSS: ' + rss_url.split('/')[2],
                                        'description': description[:150] + '...',
                                        'keywords': [query],
                                        'date': entry.get('published', 'Недавно')
                                    })
                except Exception as e:
                    print(f"Ошибка RSS {rss_url}: {e}")
        
        return results
    
    async def search_websites(self, query):
        """Прямой поиск на официальных сайтах"""
        results = []
        
        official_sites = [
            {
                'name': 'Digital.gov.ru',
                'url': 'https://digital.gov.ru/ru/',
                'search_url': 'https://digital.gov.ru/ru/search/?q='
            },
            {
                'name': 'Правительство РФ',
                'url': 'http://government.ru/',
                'search_url': 'http://government.ru/search/?q='
            },
            {
                'name': 'Минэкономразвития',
                'url': 'https://www.economy.gov.ru/',
                'search_url': 'https://www.economy.gov.ru/material/directions/reguliruemyy_sandboks/'
            }
        ]
        
        for site in official_sites:
            try:
                search_url = site.get('search_url', site['url'])
                full_url = f"{search_url}{requests.utils.quote(query)}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(full_url, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Ищем заголовки и ссылки
                            links = soup.find_all('a', href=True)
                            for link in links[:10]:
                                title = link.get_text().strip()
                                href = link['href']
                                if title and len(title) > 10:
                                    if not href.startswith('http'):
                                        href = site['url'] + href
                                    
                                    results.append({
                                        'title': title,
                                        'url': href,
                                        'source': site['name'],
                                        'description': f'Найден на {site["name"]}',
                                        'keywords': [query],
                                        'date': 'Недавно'
                                    })
            except Exception as e:
                print(f"Ошибка поиска на {site['name']}: {e}")
        
        return results
    
    def remove_duplicates(self, results):
        """Удаление дубликатов по URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        return unique_results
    
    def search_telegram_channels(self, query):
        """Поиск в Telegram каналах (через веб-интерфейс)"""
        # Это упрощенный подход - для реального парсинга TG нужен Telethon с API
        return [{
            'title': f'Результаты поиска в Telegram: {query}',
            'url': f'https://t.me/s/{query}',
            'source': 'Telegram',
            'description': 'Используйте поиск в Telegram для более точных результатов',
            'keywords': [query],
            'date': 'Сегодня'
        }]

# Упрощенная версия для тестирования
class SimpleNewsParser:
    def __init__(self):
        self.config = Config()
    
    async def search_all_sources(self, query):
        """Упрощенный поиск с тестовыми данными"""
        # Тестовые данные для демонстрации
        test_data = [
            {
                'title': 'Развитие регуляторных песочниц в России - последние новости',
                'url': 'https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/',
                'source': 'Digital.gov.ru',
                'description': 'Официальная информация о регуляторных песочницах в РФ',
                'keywords': [query],
                'date': '2024'
            },
            {
                'title': 'Экспериментальные правовые режимы: новые проекты',
                'url': 'https://www.economy.gov.ru/material/directions/reguliruemyy_sandboks/',
                'source': 'Минэкономразвития',
                'description': 'Информация о регулируемых сэндбоксах для бизнеса',
                'keywords': [query],
                'date': '2024'
            },
            {
                'title': 'Цифровые инновации и правовые эксперименты',
                'url': 'https://ria.ru/digital_economy/',
                'source': 'РИА Новости',
                'description': 'Новости о цифровой экономике и правовых инновациях',
                'keywords': [query],
                'date': '2024'
            },
            {
                'title': 'Правовые режимы для технологического развития',
                'url': 'https://www.vedomosti.ru/tags/цифровая%20экономика',
                'source': 'Ведомости',
                'description': 'Аналитика и новости о технологиях и праве',
                'keywords': [query],
                'date': '2024'
            }
        ]
        
        return test_data
