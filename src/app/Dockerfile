FROM python:3.10-slim

WORKDIR /app

# pour healthchecks (netcat) et curl
RUN apt-get update && apt-get install -y netcat-openbsd curl

# 1) installer les dépendances Python
COPY src/app/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 2) copier l'app Flask
COPY src/app /app

# 3) copier le dossier ms_montantmax
COPY src/ms_montantmax /app/ms_montantmax

# 4) ajouter ms_montantmax à PYTHONPATH pour les imports top-level
ENV PYTHONPATH="/app/ms_montantmax:${PYTHONPATH}"

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
