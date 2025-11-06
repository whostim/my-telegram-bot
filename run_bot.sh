#!/bin/bash

# Останавливаем все возможные процессы бота
echo "🛑 Останавливаем все процессы бота..."
pkill -9 -f "universal_search_bot.py" 2>/dev/null
pkill -9 -f "python.*universal_search_bot" 2>/dev/null

# Ждем завершения
sleep 3

# Очищаем вебхук через API Telegram
echo "🔧 Очищаем вебхук..."
source .env
curl -s "https://api.telegram.org/bot$BOT_TOKEN/deleteWebhook" > /dev/null

# Запускаем бота с python3
echo "🚀 Запускаем бота..."
python3 universal_search_bot.py
