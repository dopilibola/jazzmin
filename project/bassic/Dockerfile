# Python imijidan foydalanamiz
FROM python:3.10

WORKDIR /bassic

# requirements.txt faylini ko‘chirib, kerakli kutubxonalarni o‘rnatamiz
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Hammasini ko‘chirib olish
COPY . .

# start.sh faylini bajarish huquqi beramiz
RUN chmod +x start.sh


# EntryPointni sozlash
ENTRYPOINT ["./start.sh"]

EXPOSE 8000
# Agar start.sh fayli to‘g‘ri bajarilsa, Django serverni ishga tushiradi
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]