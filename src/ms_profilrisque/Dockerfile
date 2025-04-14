# Utiliser une image Python 3.10 slim
FROM python:3.13-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer curl et netcat-openbsd pour les healthchecks
RUN apt-get update && apt-get install -y curl

# Installer les dépendances nécessaires : Flask et Graphene
RUN pip install --upgrade pip && \
    pip install flask graphene

# Copier le code source dans le conteneur
COPY . .

# Exposer le port utilisé (ici 5001)
EXPOSE 5001

# Lancer l’application
CMD ["python", "server.py"]
