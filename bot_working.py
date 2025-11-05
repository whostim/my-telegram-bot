import os
import logging
import asyncio
import random
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📰 Свежие новости"), KeyboardButton(text="🔍 Поиск")],
        [KeyboardButton(text="🚀 Тренды"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

class DemoNewsParser:
    def __init__(self):
        self.demo_news = [
            {
                'title': '🎯 В России расширяют применение регуляторных песочниц',
                'url': 'https://digital.gov.ru/ru/activity/directions/regulatory_sandbox/',
                'source': 'Digital.gov.ru',
                'description': 'Новые проекты в области экспериментальных правовых режимов получают поддержку',
                'keywords': ['песочница', 'регуляторная'],
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': '📈 ЭПР для fintech: новые возможности для стартапов',
                'url': 'https://www.cbr.ru/fintech/',
                'source': 'ЦБ РФ',
                'description': 'Центробанк рассматривает новые заявки в регуляторной песочнице',
                'keywords': ['ЭПР', 'fintech', 'песочница'],
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': '🔬 Экспериментальный правовой режим в здравоохранении',
                'url': 'https://minzdrav.gov.ru/',
                'source': 'Минздрав РФ',
                'description': 'Новые медицинские технологии получают особые правовые условия',
                'keywords': ['экспериментальный', 'правовой режим'],
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': '💡 Цифровая песочница: итоги 2024 года',
                'url': 'https://www.economy.gov.ru/',
                'source': 'Минэкономразвития',
                'description': 'Подведены итоги работы цифровых регуляторных песочниц',
                'keywords': ['цифровая', 'песочница'],
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp()
            },
            {
                'title': '🚀 Новые правовые эксперименты в AI и big data',
                'url': 'https://www.vedomosti.ru/technology',
                'source': 'Ведомости',
                'description': 'Россия расширяет эксперименты с правовыми режимами для ИИ',
                'keywords': ['правовой', 'эксперимент', 'AI'],
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': datetime.now().timestamp()
            }
        ]
    
    async def search_news(self, query=None, hours_back=24):
        """Имитация поиска новостей"""
        await asyncio.sleep(1)  # Имитация задержки поиска
        
        if query:
            # Фильтруем по запросу
            query_lower = query.lower()
            filtered = [
                item for item in self.demo_news 
                if any(keyword in query_lower for keyword in item['keywords'] + [query_lower])
            ]
            return filtered if filtered else random.sample(self.demo_news, min(3, len(self.demo_news)))
        else:
            # Возвращаем все новости
            return self.demo_news
    
    async def get_trending(self):
        """Трендовые новости"""
        await asyncio.sleep(0.5)
        return random.sample(self.demo_news, min(3, len(self.demo_news)))

# Инициализируем парсер
news_parser = DemoNewsParser()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {user_name}!\n"
        "Я бот для поиска новостей об экспериментально-правовых режимах РФ.\n\n"
        "🔍 **Сейчас в демо-режиме:**\n"
        "• Показываю примеры новостей\n"
        "• Готов к настройке реального поиска\n\n"
        "Используйте кнопки ниже для работы:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Доступные команды:**\n\n"
        "Кнопки:\n"
        "• 📰 Свежие новости - примеры статей\n"
        "• 🔍 Поиск - найти по ключевым словам\n"
        "• 🚀 Тренды - популярные темы\n"
        "• ℹ️ Помощь - эта информация\n\n"
        "🔍 **Примеры запросов:**\n"
        "• песочница\n"
        "• ЭПР\n"
        "• регуляторный эксперимент\n"
        "• цифровая песочница"
    )

@dp.message(lambda message: message.text == "📰 Свежие новости")
async def fresh_news(message: types.Message):
    await message.answer("🔍 Ищу свежие новости...")
    
    try:
        news_items = await news_parser.search_news()
        
        response = "📰 **Примеры новостей (демо-режим):**\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"📝 {item['description']}\n\n"
        
        response += "💡 *Это демо-данные. Настраиваю реальный поиск...*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Временная ошибка. Попробуйте позже.")

@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_menu(message: types.Message):
    await message.answer(
        "🔍 **Поиск новостей**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры:\n"
        "• `песочница`\n"
        "• `ЭПР`\n"
        "• `регуляторный эксперимент`\n"
        "• `цифровая песочница`\n\n"
        "💡 *Сейчас в демо-режиме*",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "🚀 Тренды")
async def trends_news(message: types.Message):
    await message.answer("📈 Ищу трендовые новости...")
    
    try:
        news_items = await news_parser.get_trending()
        
        response = "📈 **Трендовые темы (демо):**\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"🏷️ Ключевые слова: {', '.join(item['keywords'])}\n\n"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Временная ошибка.")

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def about_bot(message: types.Message):
    await message.answer(
        "ℹ️ **Информация о боте:**\n\n"
        "🤖 **Текущий статус:** Демо-режим\n"
        "🔧 **Что работает:** Показ примеров новостей\n"
        "🚧 **В разработке:** Реальный поиск по источникам\n\n"
        "📚 **Планируемые источники:**\n"
        "• Telegram каналы\n"
        "• Новостные сайты\n"
        "• Официальные порталы\n"
        "• RSS ленты\n\n"
        "💡 Для настройки реального поиска нужны дополнительные настройки."
    )

@dp.message()
async def handle_text(message: types.Message):
    """Обработка текстовых запросов"""
    user_text = message.text.strip()
    
    if user_text.startswith('/') or user_text in ["📰 Свежие новости", "🚀 Тренды", "🔍 Поиск", "ℹ️ Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_news(user_text)
        
        response = f"🔍 **Результаты по '{user_text}' (демо):**\n\n"
        
        for i, item in enumerate(news_items, 1):
            response += f"**{i}. {item['title']}**\n"
            response += f"🔗 [Читать]({item['url']})\n"
            response += f"📌 {item['source']}\n"
            response += f"📝 {item['description']}\n\n"
        
        response += "💡 *Это демо-данные. Реальный поиск настраивается...*"
        
        await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer("❌ Ошибка поиска. Попробуйте другой запрос.")

async def main():
    logger.info("Демо-бот запускается...")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка вебхука: {e}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
