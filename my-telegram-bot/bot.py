import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import urllib.parse

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение токена бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле")
    logger.error("💡 Создайте файл .env с содержимым: BOT_TOKEN=ваш_токен")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создание клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск статей"), KeyboardButton(text="📢 Поиск в TG")],
        [KeyboardButton(text="⚡ Новости ЭПР"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

class ContentSearcher:
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def search_articles(self, query):
        """Поиск статей по теме"""
        # Здесь будет реальный парсинг сайтов
        # Пока используем заглушку с примерами
        
        articles = [
            {
                'title': 'Экспериментальные правовые режимы в России: новые возможности',
                'url': 'https://www.rbc.ru/finances/01/12/2024/1234567890abcdef',
                'description': 'Расширение перечня ЭПР для финтех-компаний в 2024 году',
                'source': 'RBC',
                'date': '01.12.2024'
            },
            {
                'title': 'Регуляторная песочница: итоги работы за 2023 год',
                'url': 'https://www.vedomosti.ru/finance/30/11/2024/1234567890',
                'description': 'Банк России подвел итоги работы регуляторной песочницы',
                'source': 'Ведомости', 
                'date': '30.11.2024'
            },
            {
                'title': 'Цифровые инновации и ЭПР: новые подходы',
                'url': 'https://www.kommersant.ru/doc/1234567',
                'description': 'Развитие экспериментальных правовых режимов в цифровой экономике',
                'source': 'Коммерсант',
                'date': '28.11.2024'
            }
        ]
        
        # Фильтруем по релевантности запросу
        query_lower = query.lower()
        filtered_articles = [
            article for article in articles 
            if any(word in article['title'].lower() for word in query_lower.split())
        ]
        
        return filtered_articles if filtered_articles else articles[:2]
    
    async def search_telegram_posts(self, query):
        """Поиск постов в Telegram"""
        # Здесь будет интеграция с Telegram API
        # Пока используем заглушку
        
        posts = [
            {
                'channel': 'Росфинмониторинг',
                'channel_url': 'https://t.me/rosfinmonitoring',
                'post_url': 'https://t.me/rosfinmonitoring/1234',
                'text': 'Обновление методологии ЭПР в финансовом секторе. Новые правила вступают в силу с 1 декабря 2024 года.',
                'date': '2 часа назад',
                'views': '1.2K'
            },
            {
                'channel': 'Банк России',
                'channel_url': 'https://t.me/centralbank_russia',
                'post_url': 'https://t.me/centralbank_russia/5678', 
                'text': 'ЦБ утвердил новые стандарты для ЭПР в финтехе. Основные изменения касаются цифровых активов.',
                'date': '5 часов назад',
                'views': '890'
            },
            {
                'channel': 'FinTech Russia',
                'channel_url': 'https://t.me/fintech_ru',
                'post_url': 'https://t.me/fintech_ru/9012',
                'text': 'ЭПР как драйвер роста финтех-индустрии в России. Кейсы успешных проектов.',
                'date': '1 день назад',
                'views': '2.1K'
            }
        ]
        
        query_lower = query.lower()
        filtered_posts = [
            post for post in posts 
            if any(word in post['text'].lower() for word in query_lower.split())
        ]
        
        return filtered_posts if filtered_posts else posts[:2]
    
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()

# Инициализация поисковика
searcher = ContentSearcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎯 **Бот поиска контента**\n\n"
        "Я помогаю находить:\n"
        "• 🔍 Конкретные статьи и новости\n"
        "• 📢 Конкретные посты в Telegram\n"
        "• ⚡ Актуальную информацию по ЭПР\n\n"
        "Выберите тип поиска или просто напишите запрос!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
ℹ️ **Помощь по боту:**

🔍 **Поиск статей** - найдет статьи на RBC, Ведомостях, Коммерсанте
📢 **Поиск в TG** - найдет посты в Telegram каналах
⚡ **Новости ЭПР** - свежие новости по теме
ℹ️ **Помощь** - это сообщение

💡 **Просто напишите запрос** - я сам определю что искать!

**Примеры запросов:**
• ЭПР в финансах
• регуляторная песочница
• новые правила ЭПР 2024
• экспериментальный правовой режим
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Поиск статей")
async def search_articles_menu(message: types.Message):
    await message.answer("🔍 Напишите тему для поиска статей. Я найду конкретные статьи на новостных сайтах!")

@dp.message(lambda message: message.text == "📢 Поиск в TG")
async def search_telegram_menu(message: types.Message):
    await message.answer("📢 Напишите тему для поиска в Telegram. Я найду конкретные посты в каналах!")

@dp.message(lambda message: message.text == "⚡ Новости ЭПР")
async def epr_news(message: types.Message):
    await message.answer("⚡ Ищу свежие новости об ЭПР...")
    
    try:
        articles = await searcher.search_articles("ЭПР экспериментальный правовой режим")
        
        response = "⚡ **Свежие новости об ЭПР:**\n\n"
        
        for i, article in enumerate(articles, 1):
            response += f"{i}. **{article['title']}**\n"
            response += f"   📰 {article['source']} | {article['date']}\n"
            response += f"   📝 {article['description']}\n"
            response += f"   🔗 {article['url']}\n\n"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка поиска новостей ЭПР: {e}")
        await message.answer("❌ Ошибка при поиске новостей. Попробуйте позже.")

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_button(message: types.Message):
    await cmd_help(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    # Игнорируем команды и кнопки
    buttons = ["🔍 Поиск статей", "📢 Поиск в TG", "⚡ Новости ЭПР", "ℹ️ Помощь"]
    if user_text.startswith('/') or user_text in buttons:
        return
    
    await message.answer(f"🔍 Ищу контент по запросу: '{user_text}'...")
    
    try:
        # Определяем тип поиска по контексту
        if any(word in user_text.lower() for word in ['telegram', 'тг', 'tg', 'канал', 'пост']):
            # Поиск в Telegram
            posts = await searcher.search_telegram_posts(user_text)
            
            response = f"📢 **Найденные посты в Telegram по '{user_text}':**\n\n"
            
            for i, post in enumerate(posts, 1):
                response += f"{i}. **Канал:** {post['channel']}\n"
                response += f"   👁️ Просмотры: {post['views']} | {post['date']}\n"
                response += f"   📝 {post['text']}\n"
                response += f"   🔗 {post['post_url']}\n\n"
                
        else:
            # Поиск статей
            articles = await searcher.search_articles(user_text)
            
            response = f"🔍 **Найденные статьи по '{user_text}':**\n\n"
            
            for i, article in enumerate(articles, 1):
                response += f"{i}. **{article['title']}**\n"
                response += f"   📰 {article['source']} | {article['date']}\n"
                response += f"   📝 {article['description']}\n"
                response += f"   🔗 {article['url']}\n\n"
        
        if "🔍" not in response and "📢" not in response:
            response += "😔 Не удалось найти контент по вашему запросу.\n\n"
            response += "💡 Попробуйте:\n• Изменить формулировку\n• Использовать другие ключевые слова\n• Указать более конкретную тему"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        await message.answer(f"❌ Произошла ошибка при поиске. Попробуйте другой запрос.")

async def main():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск бота поиска контента...")
    
    try:
        # Удаляем вебхук и начинаем опрос
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Закрываем сессию при завершении
        await searcher.close()

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())
