# 1. Utilisation d'une image légère
FROM python:3.9-slim

# 2. Installation de FFmpeg et dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Dossier de travail
WORKDIR /app

# 4. COPPIE D'ABORD uniquement le requirements.txt
# Cela permet de mettre en cache l'installation des librairies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copie le reste des fichiers (app.py, index.html, etc.)
COPY . .

# 6. Gestion des permissions pour la base de données
RUN mkdir -p databases && chmod 777 databases

# 7. Variables d'environnement pour Flask
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 8. Lancement avec Gunicorn
# Note : on utilise 2 workers pour plus de stabilité si la RAM le permet
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]
