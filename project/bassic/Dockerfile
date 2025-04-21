# Python image asosida
FROM python:3.10


WORKDIR /app

# Requirements ishlatadi 
COPY requirements.txt .

# requ file yordam beradi 
RUN pip install --no-cache-dir -r requirements.txt

# hammasini ochadi 
COPY . .

# Port ochadi 
EXPOSE 8000

# Django serverni ishlatadi 
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
# CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

