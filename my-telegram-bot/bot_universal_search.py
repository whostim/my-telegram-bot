import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import urllib.parse
from bs4 import BeautifulSoup
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск в интернете"), KeyboardButton(text="📢 Поиск в Telegram")],
        [KeyboardButton(text="⚡ Новости ЭПР"), KeyboardButton(text="🆘 Помощь")]
    ],
    resize_keyboard=True
)

class InternetSearcher:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def search_google(self, query, num_results=5):
        """Поиск через Google (используем парсинг)"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={num_results}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    # Ищем основные результаты поиска
                    for g in soup.find_all('div', class_='g')[:num_results]:
                        link = g.find('a')
                        if link and link.get('href'):
                            title = g.find('h3')
                            snippet = g.find('span', class_='aCOpRe')
                            
                            if title:
                                result = {
                                    'title': title.get_text(),
                                    'url': link.get('href'),
                                    'snippet': snippet.get_text() if snippet else ''
                                }
                                # Фильтруем настоящие URL (не реклама)
                                if result['url'].startswith('/url?q='):
                                    result['url'] = result['url'].split('/url?q=')[1].split('&')[0]
                                    results.append(result)
                    
                    return results
                else:
                    return []
        except Exception as e:
            logger.error(f"Ошибка Google поиска: {e}")
            return []
            
    async def search_news(self, query, num_results=5):
        """Поиск новостей"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/search?q={encoded_query}&hl=ru-RU&gl=RU&ceid=RU:ru"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    # Ищем новости
                    articles = soup.find_all('article')[:num_results]
                    
                    for article in articles:
                        link = article.find('a', href=True)
                        title = article.find('h3') or article.find('h4')
                        
                        if link and title:
                            result = {
                                'title': title.get_text().strip(),
                                'url': f"https://news.google.com{link['href']}",
                                'snippet': 'Новость от Google News'
                            }
                            results.append(result)
                    
                    return results
                else:
                    return []
        except Exception as e:
            logger.error(f"Ошибка поиска новостей: {e}")
            return []
            
    async def search_yandex_news(self, query, num_results=5):
        """Поиск в Яндекс.Новостях"""
        try:
            session = await self.get_session()
            encoded_query = urllib.parse.quote(query)
            url = f"https://yandex.ru/news/search?text={encoded_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    # Ищем карточки новостей
                    news_cards = soup.find_all('div', class_='mg-card')[:num_results]
                    
                    for card in news_cards:
                        title_elem = card.find('h2') or card.find('a', class_='mg-card__link')
                        source_elem = card.find('span', class_='mg-card-source__source')
                        
                        if title_elem:
                            result = {
                                'title': title_elem.get_text().strip(),
                                'url': title_elem.get('href') if title_elem.get('href') else f"https://yandex.ru/news/search?text={encoded_query}",
                                'snippet': source_elem.get_text() if source_elem else 'Яндекс.Новости'
                            }
                            # Добавляем полный URL если относительный
                            if result['url'].startswith('/'):
                                result['url'] = f"https://yandex.ru{result['url']}"
                            results.append(result)
                    
                    return results
                else:
                    return []
        except Exception as e:
            logger.error(f"Ошибка Яндекс.Новостей: {e}")
            return []

class TelegramSearcher:
    async def search_telegram_channels(self, query):
        """Поиск по известным каналам об ЭПР"""
        # Список каналов, которые могут содержать информацию об ЭПР
        channels = [
            {"name": "📊 Росфинмониторинг", "url": "https://t.me/rosfinmonitoring", "topics": ["ЭПР", "регуляторная песочница"]},
            {"name": "🚀 Инновации в финансах", "url": "https://t.me/fintech_ru", "topics": ["ЭПР", "финтех"]},
            {"name": "🏦 Банк России", "url": "https://t.me/centralbank_russia", "topics": ["регуляторика", "ЭПР"]},
            {"name": "💡 Цифровая экономика", "url": "https://t.me/digital_economy", "topics": ["ЭПР", "инновации"]},
        ]
        
        results = []
        query_lower = query.lower()
        
        for channel in channels:
            # Проверяем соответствие запросу по темам
            if any(topic.lower() in query_lower for topic in channel['topics']):
                results.append({
                    'title': channel['name'],
                    'url': channel['url'],
                    'snippet': f"Канал по теме: {', '.join(channel['topics'])}"
                })
        
        # Если нет точных совпадений, возвращаем общие каналы
        if not results:
            for channel in channels[:2]:
                results.append({
                    'title': channel['name'],
                    'url': channel['url'],
                    'snippet': "Возможно содержит информацию по вашему запросу"
                })
                
        return results

# Инициализация поисковиков
internet_searcher = InternetSearcher()
telegram_searcher = TelegramSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌍 Умный поисковый бот\n\n"
        "Я могу:\n"
        "• 🔍 Искать реальные статьи в интернете\n"
        "• 📢 Находить релевантные Telegram-каналы\n"
        "• ⚡ Показывать свежие новости об ЭПР\n\n"
        "Просто напишите что ищете!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🆘 Помощь по боту:

🔍 **Поиск в интернете** - найдет реальные статьи и новости
📢 **Поиск в Telegram** - найдет релевантные каналы
⚡ **Новости ЭПР** - свежие новости об экспериментальных правовых режимах

💡 **Просто напишите любой запрос** - я сам определю где лучше искать!

Примеры запросов:
• "ЭПР в финансовом секторе"
• "регуляторная песочница 2024"
• "последние новости об ЭПР"
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Поиск в интернете")
async def search_internet_menu(message: types.Message):
    await message.answer("🔍 Напишите запрос для поиска в интернете. Я найду реальные статьи и новости!")

@dp.message(lambda message: message.text == "📢 Поиск в Telegram")
async def search_telegram_menu(message: types.Message):
    await message.answer("📢 Напишите запрос для поиска в Telegram. Я найду релевантные каналы!")

@dp.message(lambda message: message.text == "⚡ Новости ЭПР")
async def epr_news(message: types.Message):
    await message.answer("🔍 Ищу свежие новости об ЭПР...")
    
    try:
        # Поиск в Google News
        news_results = await internet_searcher.search_news("ЭПР экспериментальный правовой режим Россия", 5)
        yandex_news = await internet_searcher.search_yandex_news("ЭПР", 3)
        
        response = "⚡ **Последние новости об ЭПР:**\n\n"
        
        if news_results or yandex_news:
            all_news = news_results + yandex_news
            seen_titles = set()
            
            for i, news in enumerate(all_news[:6], 1):
                if news['title'] not in seen_titles:
                    seen_titles.add(news['title'])
                    response += f"{i}. **{news['title']}**\n"
                    response += f"   📝 {news['snippet']}\n"
                    response += f"   🔗 {news['url']}\n\n"
        else:
            response += "😔 Не удалось найти свежие новости.\n"
            response += "Попробуйте поискать вручную:\n"
            response += "• https://news.google.com/search?q=ЭПР+Россия\n"
            response += "• https://yandex.ru/news/search?text=ЭПР\n"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка поиска новостей ЭПР: {e}")
        await message.answer("❌ Ошибка при поиске новостей. Попробуйте позже.")

@dp.message(lambda message: message.text == "🆘 Помощь")
async def help_button(message: types.Message):
    await cmd_help(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    if user_text.startswith('/') or user_text in ["🔍 Поиск в интернете", "📢 Поиск в Telegram", "⚡ Новости ЭПР", "🆘 Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу: '{user_text}'...")
    
    try:
        # Определяем тип запроса
        if any(word in user_text.lower() for word in ['telegram', 'тг', 'канал', 'чат']):
            # Поиск в Telegram
            telegram_results = await telegram_searcher.search_telegram_channels(user_text)
            
            response = f"📢 **Релевантные Telegram-каналы для '{user_text}':**\n\n"
            
            if telegram_results:
                for i, result in enumerate(telegram_results, 1):
                    response += f"{i}. **{result['title']}**\n"
                    response += f"   📝 {result['snippet']}\n"
                    response += f"   🔗 {result['url']}\n\n"
            else:
                response += "😔 Не нашел подходящих каналов.\n"
                response += f"Попробуйте поискать вручную: https://t.me/search?q={urllib.parse.quote(user_text)}"
                
        else:
            # Поиск в интернете
            google_results = await internet_searcher.search_google(user_text, 4)
            news_results = await internet_searcher.search_news(user_text, 3)
            
            response = f"🌐 **Результаты поиска для '{user_text}':**\n\n"
            
            if google_results or news_results:
                # Объединяем результаты
                all_results = google_results + news_results
                seen_urls = set()
                
                for i, result in enumerate(all_results[:5], 1):
                    if result['url'] not in seen_urls:
                        seen_urls.add(result['url'])
                        response += f"{i}. **{result['title']}**\n"
                        if result['snippet']:
                            snippet = result['snippet'][:100] + "..." if len(result['snippet']) > 100 else result['snippet']
                            response += f"   📝 {snippet}\n"
                        response += f"   🔗 {result['url']}\n\n"
            else:
                response += "😔 Не удалось найти результаты.\n"
                response += f"Попробуйте поискать вручную:\n"
                response += f"• https://www.google.com/search?q={urllib.parse.quote(user_text)}\n"
                response += f"• https://news.google.com/search?q={urllib.parse.quote(user_text)}\n"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        await message.answer(f"❌ Произошла ошибка. Прямые ссылки для поиска:\n"
                           f"• Google: https://www.google.com/search?q={urllib.parse.quote(user_text)}\n"
                           f"• Telegram: https://t.me/search?q={urllib.parse.quote(user_text)}")

async def main():
    logger.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
