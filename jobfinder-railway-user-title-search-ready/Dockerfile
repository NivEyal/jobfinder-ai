FROM python:3.12-slim

WORKDIR /app

# bust layer cache on every change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "start.sh"]
