FROM python:3.12-slim

WORKDIR /app

# Copiar la carpeta src completa
COPY src/ /app

# Instalar dependencias
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

CMD ["python", "ig_scraper.py"]
