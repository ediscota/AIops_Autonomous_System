FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We use python -u to force unbuffered stdout so logs show up in Docker immediately
CMD ["python", "-u", "main.py"]