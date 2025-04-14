# Utiliser l'image Python 3.13-slim
FROM python:3.13-slim

# Définir le répertoire de travail dans le container sur /app
WORKDIR /app

# Installer curl et netcat-openbsd pour les healthchecks
RUN apt-get update && apt-get install -y netcat-openbsd

# Ajouter le dossier contenant les modules générés au PYTHONPATH
ENV PYTHONPATH="/app/ms_montantmax:${PYTHONPATH}"

# Copier le dossier ms_montantmax dans /app
COPY . ./ms_montantmax

# Installer les dépendances Python (grpcio et grpcio-tools)
RUN pip install --upgrade pip && \
    pip install grpcio grpcio-tools

# Exposer le port utilisé par le service gRPC
EXPOSE 50051

# Lancer le service gRPC en utilisant le module dans le package
CMD ["python", "-m", "ms_montantmax.server"]
