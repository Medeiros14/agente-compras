FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Roda sem root: usuário de sistema sem shell nem privilégios.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 8001
CMD ["python", "-m", "app.server"]
