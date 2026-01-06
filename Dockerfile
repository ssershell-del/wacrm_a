FROM python:3.11-slim

# Installation de FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On installe les librairies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On copie tout le projet
COPY . .

# Création du dossier database
RUN mkdir -p databases && chmod 777 databases

# Lancement avec un timeout long pour l'IA
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]
