import os
import asyncio
from aiohttp import web
import universal_search_bot

async def handle(request):
    return web.Response(text="🚀 Новостной бот работает! Отправьте сообщение в Telegram боту.")

async def start_bot():
    try:
        await universal_search_bot.main()
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")

async def init_app():
    app = web.Application()
    app.router.add_get('/', handle)
    
    asyncio.create_task(start_bot())
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    web.run_app(init_app(), host='0.0.0.0', port=port)
