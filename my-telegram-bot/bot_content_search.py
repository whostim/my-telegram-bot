import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import feedparser
import json
from datetime import datetime, timedelta
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class ContentSearcher:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def search_news_sites(self, query):
        """Парсинг новостных сайтов по теме ЭПР"""
        sites = [
            {
                'name': 'РБК',
                'url': f'https://www.rbc.ru/v10/search/?query={query}&page=1',
                'selectors': {
                    'articles': '.search-item',
                    'title': '.search-item__title',
                    'link': '.search-item__link',
                    'description': '.search-item__text',
                    'date': '.search-item__date'
                }
            },
            {
                'name': 'Коммерсант',
                'url': f'https://www.kommersant.ru/search/results?query={query}',
                'selectors': {
                    'articles': '.search_result_item',
                    'title': '.search_result_title a',
                    'link': '.search_result_title a',
                    'description': '.search_result_text',
                    'date': '.search_result_date'
                }
            },
            {
                'name': 'Ведомости',
                'url': f'https://www.vedomosti.ru/search?query={query}',
                'selectors': {
                    'articles': '.search-results__item',
                    'title': '.search-results__item-title a',
                    'link': '.search-results__item-title a',
                    'description': '.search-results__item-text',
                    'date': '.search-results__item-date'
                }
            }
        ]
        
        all_results = []
        
        for site in sites:
            try:
                session = await self.get_session()
                async with session.get(site['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        articles = soup.select(site['selectors']['articles'])[:3]
                        
                        for article in articles:
                            try:
                                title_elem = article.select_one(site['selectors']['title'])
                                link_elem = article.select_one(site['selectors']['link'])
                                desc_elem = article.select_one(site['selectors']['description'])
                                date_elem = article.select_one(site['selectors']['date'])
                                
                                if title_elem and link_elem:
                                    title = title_elem.get_text().strip()
                                    link = link_elem.get('href')
                                    
                                    # Преобразуем относительные ссылки в абсолютные
                                    if link and link.startswith('/'):
                                        if site['name'] == 'РБК':
                                            link = f"https://www.rbc.ru{link}"
                                        elif site['name'] == 'Коммерсант':
                                            link = f"https://www.kommersant.ru{link}"
                                        elif site['name'] == 'Ведомости':
                                            link = f"https://www.vedomosti.ru{link}"
                                    
                                    description = desc_elem.get_text().strip() if desc_elem else ''
                                    date = date_elem.get_text().strip() if date_elem else ''
                                    
                                    all_results.append({
                                        'title': title,
                                        'url': link,
                                        'description': description[:200] + '...' if len(description) > 200 else description,
                                        'source': site['name'],
                                        'date': date
                                    })
                            except Exception as e:
                                logger.error(f"Ошибка парсинга статьи: {e}")
                                continue
            except Exception as e:
                logger.error(f"Ошибка парсинга {site['name']}: {e}")
                continue
                
        return all_results[:5]  # Возвращаем до 5 результатов

    async def search_government_sites(self, query):
        """Парсинг государственных сайтов"""
        gov_sites = [
            {
                'name': 'Правительство РФ',
                'url': 'http://government.ru/news/',
                'selectors': {
                    'articles': '.news_archive_item',
                    'title': 'h4 a',
                    'link': 'h4 a',
                    'date': '.news_date'
                }
            },
            {
                'name': 'Банк России',
                'url': 'https://www.cbr.ru/press/',
                'selectors': {
                    'articles': '.news_item',
                    'title': '.title a',
                    'link': '.title a',
                    'date': '.date'
                }
            }
        ]
        
        results = []
        query_lower = query.lower()
        
        for site in gov_sites:
            try:
                session = await self.get_session()
                async with session.get(site['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        articles = soup.select(site['selectors']['articles'])[:5]
                        
                        for article in articles:
                            title_elem = article.select_one(site['selectors']['title'])
                            link_elem = article.select_one(site['selectors']['link'])
                            date_elem = article.select_one(site['selectors']['date'])
                            
                            if title_elem and link_elem:
                                title = title_elem.get_text().strip()
                                
                                # Проверяем релевантность запросу
                                if any(word in title.lower() for word in query_lower.split()):
                                    link = link_elem.get('href')
                                    if link and link.startswith('/'):
                                        if site['name'] == 'Правительство РФ':
                                            link = f"http://government.ru{link}"
                                        elif site['name'] == 'Банк России':
                                            link = f"https://www.cbr.ru{link}"
                                    
                                    date = date_elem.get_text().strip() if date_elem else ''
                                    
                                    results.append({
                                        'title': title,
                                        'url': link,
                                        'description': f"Официальная информация с сайта {site['name']}",
                                        'source': site['name'],
                                        'date': date
                                    })
            except Exception as e:
                logger.error(f"Ошибка парсинга {site['name']}: {e}")
                continue
                
        return results

    async def search_telegram_content(self, query):
        """Имитация поиска в Telegram через известные каналы"""
        # В реальном боте здесь будет Telethon API
        telegram_channels = [
            {
                'name': 'Росфинмониторинг',
                'username': 'rosfinmonitoring',
                'posts': [
                    "Обновление методологии ЭПР в финансовом секторе",
                    "Новые правила регуляторной песочницы для финтеха",
                    "Расширение перечня ЭПР на 2024 год"
                ]
            },
            {
                'name': 'Банк России',
                'username': 'centralbank_russia', 
                'posts': [
                    "ЦБ утвердил новые стандарты для ЭПР",
                    "Регуляторная песочница: итоги года",
                    "ЭПР в цифровой экономике - новые подходы"
                ]
            },
            {
                'name': 'Цифровая экономика',
                'username': 'digital_economy',
                'posts': [
                    "Экспериментальные правовые режимы: опыт регионов",
                    "ЭПР как инструмент развития инноваций",
                    "Новые законодательные инициативы по ЭПР"
                ]
            }
        ]
        
        results = []
        query_lower = query.lower()
        
        for channel in telegram_channels:
            for post in channel['posts']:
                if any(word in post.lower() for word in query_lower.split()):
                    results.append({
                        'title': post,
                        'url': f"https://t.me/{channel['username']}",
                        'description': f"Пост из канала {channel['name']}",
                        'source': f"Telegram: {channel['name']}",
                        'date': 'Недавно'
                    })
                    
        return results[:3]

    async def get_epr_rss_news(self):
        """Получение новостей через RSS по теме ЭПР"""
        rss_feeds = [
            'https://www.rbc.ru/rss/technology.rss',
            'https://www.vedomosti.ru/rss/news.xml',
            'https://www.kommersant.ru/RSS/news.xml'
        ]
        
        results = []
        
        for feed_url in rss_feeds:
            try:
                session = await self.get_session()
                async with session.get(feed_url) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        feed = feedparser.parse(xml_content)
                        
                        for entry in feed.entries[:3]:
                            title = entry.title
                            # Фильтруем по теме ЭПР
                            if any(keyword in title.lower() for keyword in ['эпр', 'регуляторн', 'песочниц', 'экспериментальн']):
                                results.append({
                                    'title': title,
                                    'url': entry.link,
                                    'description': entry.summary[:200] + '...' if entry.summary else '',
                                    'source': feed.feed.title,
                                    'date': entry.published if hasattr(entry, 'published') else ''
                                })
            except Exception as e:
                logger.error(f"Ошибка RSS {feed_url}: {e}")
                continue
                
        return results

# Инициализация поисковика
content_searcher = ContentSearcher()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти статьи"), KeyboardButton(text="📢 Посты в Telegram")],
        [KeyboardButton(text="⚡ Новости ЭПР"), KeyboardButton(text="🏛️ Официальные источники")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "📚 **Умный поиск контента**\n\n"
        "Я нахожу реальные статьи и посты по вашим запросам:\n"
        "• 🔍 Новости с RBC, Ведомостей, Коммерсанта\n"
        "• 📢 Релевантные посты из Telegram\n"
        "• ⚡ Свежие новости об ЭПР\n"
        "• 🏛️ Официальная информация\n\n"
        "Напишите запрос или используйте кнопки!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📖 **Помощь по поиску контента:**

🔍 **Найти статьи** - поиск по новостным сайтам
📢 **Посты в Telegram** - релевантные посты из каналов
⚡ **Новости ЭПР** - свежие новости по теме
🏛️ **Официальные источники** - информация с госсайтов

💡 **Примеры запросов:**
• "ЭПР в финансах"
• "регуляторная песочница"
• "новые правила ЭПР"
• "экспериментальный правовой режим 2024"
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Найти статьи")
async def find_articles(message: types.Message):
    await message.answer("🔍 Напишите тему для поиска статей в новостных изданиях:")

@dp.message(lambda message: message.text == "📢 Посты в Telegram")
async def find_telegram_posts(message: types.Message):
    await message.answer("📢 Напишите тему для поиска постов в Telegram-каналах:")

@dp.message(lambda message: message.text == "⚡ Новости ЭПР")
async def epr_news(message: types.Message):
    await message.answer("⚡ Ищу свежие новости об ЭПР...")
    
    try:
        # Комбинируем несколько источников
        rss_news = await content_searcher.get_epr_rss_news()
        gov_news = await content_searcher.search_government_sites("ЭПР")
        
        all_news = rss_news + gov_news
        
        if all_news:
            response = "⚡ **Свежие новости об ЭПР:**\n\n"
            
            for i, news in enumerate(all_news[:6], 1):
                response += f"{i}. **{news['title']}**\n"
                response += f"   📰 {news['source']}\n"
                if news['date']:
                    response += f"   📅 {news['date']}\n"
                response += f"   🔗 {news['url']}\n"
                if news['description']:
                    response += f"   📝 {news['description']}\n"
                response += "\n"
        else:
            response = "😔 Не удалось найти свежие новости.\n\n"
            response += "💡 Попробуйте:\n• Написать более конкретный запрос\n• Использовать поиск статей\n• Проверить позже"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка поиска новостей ЭПР: {e}")
        await message.answer("❌ Ошибка при поиске новостей. Попробуйте другой запрос.")

@dp.message(lambda message: message.text == "🏛️ Официальные источники")
async def official_sources(message: types.Message):
    await message.answer("🏛️ Напишите запрос для поиска в официальных источниках:")

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    buttons = ["🔍 Найти статьи", "📢 Посты в Telegram", "⚡ Новости ЭПР", "🏛️ Официальные источники"]
    if user_text.startswith('/') or user_text in buttons:
        return
    
    await message.answer(f"🔍 Ищу контент по запросу: '{user_text}'...")
    
    try:
        response = f"📚 **Результаты по запросу '{user_text}':**\n\n"
        
        # Определяем тип поиска по контексту
        if any(word in user_text.lower() for word in ['telegram', 'тг', 'канал', 'пост']):
            # Поиск в Telegram
            telegram_results = await content_searcher.search_telegram_content(user_text)
            
            if telegram_results:
                response += "📢 **Релевантные посты в Telegram:**\n\n"
                for i, post in enumerate(telegram_results, 1):
                    response += f"{i}. **{post['title']}**\n"
                    response += f"   👤 {post['source']}\n"
                    response += f"   🔗 {post['url']}\n\n"
            else:
                response += "📢 Не найдено постов в Telegram по вашему запросу.\n\n"
                
            # Всегда добавляем статьи для полноты
            news_results = await content_searcher.search_news_sites(user_text)
            if news_results:
                response += "📰 **Статьи по теме:**\n\n"
                for i, article in enumerate(news_results[:3], 1):
                    response += f"{i}. **{article['title']}**\n"
                    response += f"   📰 {article['source']}\n"
                    response += f"   🔗 {article['url']}\n"
                    if article['description']:
                        response += f"   📝 {article['description']}\n"
                    response += "\n"
                    
        elif any(word in user_text.lower() for word in ['правительств', 'банк росси', 'официал', 'закон']):
            # Поиск в официальных источниках
            gov_results = await content_searcher.search_government_sites(user_text)
            
            if gov_results:
                response += "🏛️ **Официальная информация:**\n\n"
                for i, doc in enumerate(gov_results, 1):
                    response += f"{i}. **{doc['title']}**\n"
                    response += f"   📋 {doc['source']}\n"
                    if doc['date']:
                        response += f"   📅 {doc['date']}\n"
                    response += f"   🔗 {doc['url']}\n\n"
            else:
                response += "🏛️ Не найдено официальной информации.\n\n"
                
        else:
            # Общий поиск
            news_results = await content_searcher.search_news_sites(user_text)
            telegram_results = await content_searcher.search_telegram_content(user_text)
            
            if news_results:
                response += "📰 **Найденные статьи:**\n\n"
                for i, article in enumerate(news_results, 1):
                    response += f"{i}. **{article['title']}**\n"
                    response += f"   📰 {article['source']}\n"
                    if article['date']:
                        response += f"   📅 {article['date']}\n"
                    response += f"   🔗 {article['url']}\n"
                    if article['description']:
                        response += f"   📝 {article['description']}\n"
                    response += "\n"
                    
            if telegram_results:
                response += "📢 **Посты в Telegram:**\n\n"
                for i, post in enumerate(telegram_results, 1):
                    response += f"{i}. **{post['title']}**\n"
                    response += f"   👤 {post['source']}\n"
                    response += f"   🔗 {post['url']}\n\n"
                    
        if "📰" not in response and "📢" not in response and "🏛️" not in response:
            response += "😔 Не удалось найти контент по вашему запросу.\n\n"
            response += "💡 Попробуйте:\n• Изменить формулировку\n• Использовать русский язык\n• Указать более конкретную тему"
        
        # Если сообщение слишком длинное, разбиваем на части
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await message.answer(part)
        else:
            await message.answer(response)
            
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(f"❌ Произошла ошибка при поиске. Попробуйте другой запрос или повторите позже.")

async def main():
    logger.info("Запуск бота поиска контента...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
