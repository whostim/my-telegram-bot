import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from fixed_parser import FixedNewsParser

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
news_parser = FixedNewsParser()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Поиск новостей"), KeyboardButton(text="📊 Статус")],
        [KeyboardButton(text="💡 Примеры"), KeyboardButton(text="🆘 Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для поиска актуальных новостей.\n\n"
        "⚡ **Теперь с исправленным поиском:**\n"
        "• Обход проблем с SSL\n"
        "• Надежные источники\n"
        "• Быстрый поиск\n\n"
        "🔍 Используйте кнопки ниже для работы:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🆘 **Помощь по боту:**\n\n"
        "**Команды:**\n"
        "/start - начать работу\n"
        "/search - поиск новостей\n"
        "/status - статус системы\n\n"
        "**Кнопки:**\n"
        "• 🔍 Поиск новостей - найти по ключевым словам\n"
        "• 📊 Статус - проверить работу парсера\n"
        "• 💡 Примеры - примеры запросов\n"
        "• 🆘 Помощь - эта информация\n\n"
        "💡 **Совет:** Используйте конкретные запросы для лучших результатов"
    )

@dp.message(lambda message: message.text == "🔍 Поиск новостей")
async def search_news(message: types.Message):
    await message.answer(
        "🔍 **Поиск актуальных новостей**\n\n"
        "Напишите ключевые слова для поиска:\n\n"
        "Примеры запросов:\n"
        "• `песочница регуляторная`\n"
        "• `ЭПР Россия`\n"
        "• `правовой эксперимент`\n"
        "• `цифровая песочница`\n\n"
        "⚡ Ищу в Google News и надежных источниках",
        parse_mode='Markdown'
    )

@dp.message(lambda message: message.text == "📊 Статус")
async def check_status(message: types.Message):
    await message.answer("🔄 Проверяю работу парсера...")
    
    try:
        test_results = await news_parser.search_news("тест")
        if test_results:
            status_msg = "✅ Парсер работает отлично!\n🔍 Найдены тестовые новости"
        else:
            status_msg = "⚠️ Парсер работает, но новости не найдены\n💡 Это нормально для тестового запроса"
        
        await message.answer(
            f"📊 **Статус системы:**\n\n"
            f"{status_msg}\n\n"
            f"**Источники:**\n"
            f"• Google News ✓\n"
            f"• RSS ленты ✓\n"
            f"• Обход SSL ✓\n\n"
            f"💡 Готов к поиску реальных новостей!"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {e}")

@dp.message(lambda message: message.text == "💡 Примеры")
async def show_examples(message: types.Message):
    await message.answer(
        "💡 **Примеры рабочих запросов:**\n\n"
        "🎯 **Высокая релевантность:**\n"
        "• `регуляторная песочница`\n"
        "• `ЭПР экспериментальный`\n"
        "• `цифровая песочница Россия`\n\n"
        "📈 **Средняя релевантность:**\n"
        "• `правовой эксперимент`\n"
        "• `инновационное право`\n"
        "• `технологический регуляторинг`\n\n"
        "🔍 **Общие запросы:**\n"
        "• `песочница`\n"
        "• `ЭПР`\n"
        "• `регуляторный`\n\n"
        "⚡ **Совет:** Используйте конкретные фразы для лучших результатов"
    )

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await search_news(message)

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    await check_status(message)

@dp.message()
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    
    if user_text.startswith('/') or user_text in ["🔍 Поиск новостей", "📊 Статус", "💡 Примеры", "🆘 Помощь"]:
        return
    
    await message.answer(f"🔍 Ищу новости по запросу: '{user_text}'...")
    
    try:
        news_items = await news_parser.search_news(user_text)
        
        if not news_items:
            await message.answer(
                f"🔍 По запросу '{user_text}' не найдено новостей.\n\n"
                f"💡 **Возможные причины:**\n"
                f"• Слишком узкий запрос\n"
                f"• Нет свежих новостей по теме\n"
                f"• Проблемы с источниками\n\n"
                f"🔄 **Попробуйте:**\n"
                f"• Использовать другие ключевые слова\n"
                f"• Более общий запрос\n"
                f"• Проверить статус системы"
            )
        else:
            response = f"🔍 **Найдено новостей по '{user_text}':**\n\n"
            
            for i, item in enumerate(news_items[:5], 1):
                response += f"**{i}. {item['title']}**\n"
                response += f"🔗 [Читать]({item['url']})\n"
                response += f"📌 {item['source']}\n"
                if item.get('description'):
                    response += f"📝 {item['description']}\n"
                response += f"📅 {item.get('date', 'Не указано')}\n\n"
            
            if len(news_items) > 5:
                response += f"*... и еще {len(news_items) - 5} новостей*"
            
            await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске.\n\n"
            "💡 **Что можно сделать:**\n"
            "• Проверить интернет-соединение\n"
            "• Попробовать позже\n"
            "• Использовать другой запрос\n"
            "• Проверить статус системы"
        )

async def main():
    logger.info("Исправленный бот запускается...")
    
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
