# Utilisation de Python 3.11 (plus récent et supporté)
FROM python:3.11-slim

# Installation de FFmpeg (nécessaire pour yt-dlp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tous les fichiers (app.py, index.html, youtube_cookies.txt)
COPY . .

# Création du dossier database avec les bonnes permissions
RUN mkdir -p databases && chmod 777 databases

# Port utilisé par Render
EXPOSE 5000

# Lancement avec Gunicorn (timeout long pour l'analyse vidéo)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]
