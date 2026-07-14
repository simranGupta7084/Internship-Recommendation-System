FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
EXPOSE 5000

CMD gunicorn -b 0.0.0.0:${PORT:-5000} app:app --workers 1 --timeout 120
