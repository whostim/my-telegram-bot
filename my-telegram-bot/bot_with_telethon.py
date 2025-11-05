import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import InputMessagesFilterEmpty
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.error("❌ Не все переменные окружения установлены")
    exit(1)

# Инициализация бота и клиента Telethon
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AdvancedTelegramSearcher:
    def __init__(self):
        self.telethon_client = None
        
    async def init_telethon(self):
        """Инициализация Telethon клиента"""
        if not self.telethon_client:
            self.telethon_client = TelegramClient('session_name', int(API_ID), API_HASH)
            await self.telethon_client.start()
        return self.telethon_client
        
    async def search_telegram_messages(self, query, channels=None):
        """Поиск сообщений в Telegram каналах"""
        if not channels:
            channels = [
                'rosfinmonitoring',      # Росфинмониторинг
                'centralbank_russia',    # Банк России
                'fintech_ru',           # FinTech Russia
                'digital_economy',      # Цифровая экономика
                'rg_russia',            # Российская газета
            ]
            
        results = []
        
        try:
            client = await self.init_telethon()
            
            for channel in channels:
                try:
                    # Ищем сообщения в канале
                    async for message in client.iter_messages(
                        channel, 
                        search=query,
                        limit=5
                    ):
                        if message.text:
                            # Создаем ссылку на конкретное сообщение
                            message_link = f"https://t.me/{channel}/{message.id}"
                            
                            results.append({
                                'channel': channel,
                                'message_id': message.id,
                                'text': message.text[:300] + '...' if len(message.text) > 300 else message.text,
                                'date': message.date.strftime('%d.%m.%Y %H:%M'),
                                'link': message_link,
                                'views': getattr(message, 'views', 'N/A')
                            })
                            
                except Exception as e:
                    logger.error(f"Ошибка поиска в {channel}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка Telethon: {e}")
            
        return results[:10]  # Ограничиваем количество результатов

    async def search_telegram_global(self, query):
        """Глобальный поиск по Telegram"""
        # Этот метод требует premium аккаунт Telethon
        # В бесплатной версии используем альтернативные методы
        return await self.search_telegram_messages(query)

# Инициализация расширенного поисковика
telegram_searcher = AdvancedTelegramSearcher()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти в Telegram"), KeyboardButton(text="📢 Конкретные посты")],
        [KeyboardButton(text="🌐 Популярные каналы"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🔍 **Telegram Search Bot**\n\n"
        "Я ищу реальные посты в Telegram каналах:\n"
        "• Росфинмониторинг\n"
        "• Банк России\n" 
        "• FinTech Russia\n"
        "• И многих других\n\n"
        "Напишите что ищете!",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🔍 **Telegram Search Bot**

📢 **Найти в Telegram** - поиск по всем каналам
🔍 **Конкретные посты** - детальный поиск
🌐 **Популярные каналы** - список каналов по ЭПР
ℹ️ **Помощь** - это сообщение

💡 **Примеры запросов:**
• ЭПР
• регуляторная песочница  
• экспериментальный правовой режим
• финтех инновации

⚡ **Бот показывает:**
- Текст конкретных постов
- Ссылки на сообщения
- Дату публикации
- Канал источник
"""
    await message.answer(help_text)

@dp.message(lambda message: message.text == "🔍 Найти в Telegram")
async def search_telegram(message: types.Message):
    await message.answer("🔍 Напишите запрос для поиска по всем Telegram каналам:")

@dp.message(lambda message: message.text == "📢 Конкретные посты")
async def specific_posts(message: types.Message):
    await message.answer("📢 Напишите запрос для детального поиска конкретных постов:")

@dp.message(lambda message: message.text == "🌐 Популярные каналы")
async def popular_channels(message: types.Message):
    channels_text = """
🌐 **Популярные каналы по ЭПР и финтеху:**

📊 **Официальные:**
• @rosfinmonitoring - Росфинмониторинг
• @centralbank_russia - Банк России
• @government_russia - Правительство РФ

💡 **Экспертные:**
• @fintech_ru - FinTech Russia
• @digital_economy - Цифровая экономика
• @bankir_ru - Банки.ру

📰 **Новостные:**
• @rbc_news - РБК
• @vedomosti - Ведомости
• @kommersant_news - Коммерсант

💬 **Для поиска:** напишите запрос и выберите "Найти в Telegram"
"""
    await message.answer(channels_text)

@dp.message()
async def handle_search(message: types.Message):
    user_text = message.text.strip()
    
    buttons = ["🔍 Найти в Telegram", "📢 Конкретные посты", "🌐 Популярные каналы", "ℹ️ Помощь"]
    if user_text.startswith('/') or user_text in buttons:
        return
        
    await message.answer(f"🔍 Ищу посты в Telegram по запросу: '{user_text}'...")
    
    try:
        # Используем Telethon для реального поиска
        results = await telegram_searcher.search_telegram_messages(user_text)
        
        if results:
            response = f"📢 **Найденные посты по '{user_text}':**\n\n"
            
            for i, post in enumerate(results, 1):
                response += f"{i}. **Канал:** @{post['channel']}\n"
                response += f"   📅 {post['date']}\n"
                response += f"   👁️ Просмотры: {post['views']}\n"
                response += f"   🔗 {post['link']}\n"
                response += f"   📝 {post['text']}\n\n"
                
                # Ограничиваем длину сообщения
                if len(response) > 3500:
                    response += "... (показаны первые посты)"
                    break
                    
        else:
            response = f"😔 Не найдено постов по запросу '{user_text}'\n\n"
            response += "💡 Попробуйте:\n• Изменить запрос\n• Использовать другие ключевые слова\n• Проверить популярные каналы"
            
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(f"❌ Ошибка при поиске. Попробуйте позже.")

async def main():
    logger.info("Запуск Telegram Search Bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
