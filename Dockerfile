# On part d'une version légère de Linux avec Python
FROM python:3.9-slim

# On installe FFmpeg (OBLIGATOIRE pour traiter les vidéos)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# On prépare le dossier de travail
WORKDIR /app

# On copie les fichiers du PC vers le Serveur
COPY . /app

# On installe les librairies Python
RUN pip install --no-cache-dir -r requirements.txt

# On crée le dossier databases pour éviter les erreurs de permission
RUN mkdir -p databases && chmod 777 databases

# On lance l'application avec Gunicorn (Serveur Pro)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]