import os
import asyncio
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Новостной бот работает! Отправьте сообщение в Telegram боту."

def run_bot():
    """Запускает бота в отдельном потоке"""
    import universal_search_bot
    asyncio.run(universal_search_bot.main())

if __name__ == '__main__':
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем веб-сервер для Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
