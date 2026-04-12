#!/bin/bash

# .env faylni o'qish
set -o allexport
source .env
set +o allexport

set -e

# Lokal ishga tushirishda Docker nomidan (db) localhost'ga o'tish
if [ "$DB_HOST" = "jazzmin-db" ] && [ ! -f "/.dockerenv" ]; then
  export DB_HOST=127.0.0.1
  echo "ℹ️ DB_HOST 'jazzmin-db' aniqlanib, lokal uchun 127.0.0.1 ga o'zgartirildi"
elif [ -z "$DB_HOST" ]; then
  export DB_HOST=127.0.0.1
  echo "ℹ️ DB_HOST belgilanmagan, 127.0.0.1 ga o'rnatildi"
fi

# Lokal hostga mos SITE_URL qo'llash
if [ "$DEBUG" = "True" ] && [ ! -f "/.dockerenv" ]; then
  export SITE_URL_LOCAL=${SITE_URL_LOCAL:-http://127.0.0.1:8000}
  export SITE_URL="$SITE_URL_LOCAL"
  echo "ℹ️ DEBUG rejimi: SITE_URL lokalga o'rnatildi -> $SITE_URL"
fi

# Background protsesslarni tozalash
BOT_PID=""
cleanup() {
  if [ -n "$BOT_PID" ] && kill -0 "$BOT_PID" 2>/dev/null; then
    echo "🛑 Telegram bot to'xtatildi (PID: $BOT_PID)"
    kill "$BOT_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Django migratsiyalarini bajarish
python manage.py makemigrations
echo "makemigrations."

python manage.py migrate
echo "migrate."

python manage.py collectstatic --noinput
echo "static file done "

# Superuser yaratish (agar mavjud bo'lmasa)
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="$DJANGO_SUPERUSER_USERNAME").exists():
    User.objects.create_superuser(
        username="$DJANGO_SUPERUSER_USERNAME",
        password="$DJANGO_SUPERUSER_PASSWORD",
        email="$DJANGO_SUPERUSER_EMAIL"
    )
END

echo "Dastur ishga tushdi va superuser tayyor."

# Telegram botni ishga tushirish (grave care bot)
if [ "${START_BOT:-1}" = "1" ]; then
  echo "🤖 Telegram bot ishga tushyapti..."
  python bot_main.py &
  BOT_PID=$!
  sleep 2
  if ! kill -0 "$BOT_PID" 2>/dev/null; then
    echo "❌ Telegram bot ishga tushmadi (loglarni tekshiring)"
    exit 1
  fi
  echo "✅ Telegram bot background rejimida ishlayapti (PID: $BOT_PID)"
else
  echo "ℹ️ START_BOT=0, telegram bot ishga tushirilmaydi"
fi

# Django serverni ishga tushurish
echo "Server ishga tushdi."
python manage.py runserver 0.0.0.0:8000
