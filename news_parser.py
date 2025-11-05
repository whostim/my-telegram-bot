import aiohttp
import asyncio
import feedparser
import requests
from bs4 import BeautifulSoup
from config import Config
import re
from datetime import datetime, timedelta

class NewsParser:
    def __init__(self):
        self.config = Config()
    
    async def search_news(self, query=None):
        """Поиск новостей по ключевым словам"""
        results = []
        
        # Если не указан запрос, используем ключевые слова из конфига
        if query:
            search_keywords = [query.lower()]
        else:
            search_keywords = [kw.lower() for kw in self.config.KEYWORDS]
        
        # Ищем в RSS лентах
        rss_results = await self._search_rss(search_keywords)
        results.extend(rss_results)
        
        # Ищем на веб-сайтах
        web_results = await self._search_websites(search_keywords)
        results.extend(web_results)
        
        return results[:10]  # Возвращаем первые 10 результатов
    
    async def _search_rss(self, keywords):
        """Поиск в RSS лентах"""
        results = []
        
        async with aiohttp.ClientSession() as session:
            for rss_url in self.config.RSS_SOURCES:
                try:
                    async with session.get(rss_url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:  # Берем последние 5 записей
                                title = entry.get('title', '')
                                link = entry.get('link', '')
                                description = entry.get('description', '')
                                published = entry.get('published', '')
                                
                                # Проверяем на ключевые слова
                                content_text = f"{title} {description}".lower()
                                found_keywords = []
                                
                                for keyword in keywords:
                                    if keyword in content_text:
                                        found_keywords.append(keyword)
                                
                                if found_keywords:
                                    results.append({
                                        'title': title,
                                        'url': link,
                                        'source': 'RSS: ' + rss_url,
                                        'description': description[:200] + '...' if len(description) > 200 else description,
                                        'keywords': found_keywords,
                                        'date': published
                                    })
                                    
                except Exception as e:
                    print(f"Ошибка при парсинге RSS {rss_url}: {e}")
        
        return results
    
    async def _search_websites(self, keywords):
        """Поиск на веб-сайтах"""
        results = []
        
        for website in self.config.WEBSITES:
            try:
                response = requests.get(website, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Ищем заголовки и ссылки (упрощенный парсинг)
                    titles = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                    
                    for title in titles:
                        title_text = title.get_text().strip()
                        if title_text:
                            # Ищем родительскую ссылку
                            link = title.find_parent('a')
                            href = link.get('href') if link else website
                            
                            if not href.startswith('http'):
                                href = website + href
                            
                            # Проверяем на ключевые слова
                            content_text = title_text.lower()
                            found_keywords = []
                            
                            for keyword in keywords:
                                if keyword in content_text:
                                    found_keywords.append(keyword)
                            
                            if found_keywords:
                                results.append({
                                    'title': title_text,
                                    'url': href,
                                    'source': 'Website: ' + website,
                                    'description': 'Нажмите для перехода к статье',
                                    'keywords': found_keywords,
                                    'date': 'Не указана'
                                })
                                
            except Exception as e:
                print(f"Ошибка при парсинге сайта {website}: {e}")
        
        return results
    
    def search_google_news(self, query):
        """Поиск через Google News (упрощенный)"""
        # Это заглушка - для реального поиска нужно использовать API
        return [{
            'title': f'Новости по запросу: {query}',
            'url': f'https://news.google.com/search?q={query}',
            'source': 'Google News',
            'description': 'Нажмите для просмотра результатов поиска в Google News',
            'keywords': [query],
            'date': 'Сегодня'
        }]
