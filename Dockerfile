FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema incluyendo Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copiar la carpeta src completa
COPY src/ /app

# Instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

CMD ["python", "ig_scraper.py"]