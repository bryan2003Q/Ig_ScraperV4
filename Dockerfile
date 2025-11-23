FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema incluyendo Chrome (método moderno)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Verificar que Chrome se instaló correctamente
RUN google-chrome-stable --version

# Copiar la carpeta src completa
COPY src/ /app

# Instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

CMD ["python", "ig_scraper.py"]