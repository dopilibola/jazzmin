#!/bin/bash

# .env faylni o'qish
set -o allexport
source .env
set +o allexport

# Django migratsiyalarini bajarish
python manage.py makemigrations
echo "makemigrations."

python manage.py migrate
echo "migrate."

python bot.py
echo "bot.py ishga tushdi."

python manage.py collectstatic
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

# Django serverni ishga tushurish
python manage.py runserver 0.0.0.0:8000
echo "Server ishga tushdi."
