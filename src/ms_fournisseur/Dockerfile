# Utiliser une image Python 3.10 slim
FROM python:3.13-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Mettre à jour pip et installer Flask (et autres dépendances si besoin)
RUN pip install --upgrade pip && \
    pip install flask

# Copier le code source dans le conteneur
COPY . .

# Exposer le port utilisé par l’application (5003)
EXPOSE 5003

# Lancer l’application
CMD ["python", "server.py"]
