FROM python:3.11-slim

# Instalamos dependencias del sistema para pdf2image (poppler) y pytesseract (tesseract)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero requirements para aprovechar cache de Docker
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Ahora copiamos el resto del código
COPY . .

# Puerto donde va a correr uvicorn dentro del contenedor
EXPOSE 10000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]