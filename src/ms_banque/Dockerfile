# Utiliser une image Python 3.10 slim, compatible avec Spyne
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer curl et netcat-openbsd pour les healthchecks
RUN apt-get update && apt-get install -y netcat-openbsd

# Copier le fichier des dépendances dans le conteneur
COPY requirements.txt .

# Installer les dépendances
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copier l'intégralité du code du microservice dans le conteneur
COPY . .

# Exposer le port utilisé par le service SOAP
EXPOSE 5002

# Lancer le service en exécutant le fichier server.py
CMD ["python", "server.py"]
