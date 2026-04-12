#!/bin/bash
# Telegram botni ishga tushirish
# Usage: bash runbot.sh  (yoki chmod +x runbot.sh && ./runbot.sh)

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

# Lokal ishga tushirishda Docker nomidan (db) localhost'ga o'tish
if [ "$DB_HOST" = "jazzmin-db" ] && [ ! -f "/.dockerenv" ]; then
  export DB_HOST=127.0.0.1
fi

python bot_main.py
