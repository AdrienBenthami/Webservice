# Application Compagnon - Démarrage et utilisation

Ce README explique comment démarrer l'application compagnon (`app.py`) une fois que les microservices sont lancés via Docker Compose.

---

## 1. Démarrage des microservices

À la racine du projet, exécutez :

```bash
# Lance les micros-services (montantmax, profilrisque, banque, fournisseur)
docker compose up --build -d
```

Cela va :

- Construire et démarrer les conteneurs pour chaque microservice.  
- Exposer les ports :
  - 50051 (gRPC MontantMax)  
  - 5001 (GraphQL ProfilRisque)  
  - 5002 (SOAP Banque)  
  - 5003 (REST Fournisseur)  

Vérifiez que tous les services sont sains :  

```bash
docker compose ps
```

---

## 2. Démarrage de l'application compagnon

L'application compagnon n'est pas encore incluse dans le `docker-compose.yml` par défaut. Pour la lancer localement :

1. Placez-vous dans le répertoire `src/app` :  
   ```bash
   cd src/app
   ```
2. Activez votre environnement virtuel Python, puis installez les dépendances :  
   ```bash
   # si ce n'est pas déjà fait
   python3 -m venv env
   source env/bin/activate
   pip install flask grpcio requests
   ```
3. Lancez l'application :  
   ```bash
   python app.py
   ```

L'application démarrera sur le port **5000** et s'attendra à trouver les microservices sur :

- `localhost:50051` (MontantMax gRPC)  
- `localhost:5001` (ProfilRisque GraphQL)  
- `localhost:5002` (Banque SOAP)  
- `localhost:5003` (Fournisseur REST)  

---

## 3. Exemple d'utilisation

### Requête de prêt sans chèque

```bash
curl -X POST http://localhost:5000/loan \
  -H "Content-Type: application/json" \
  -d '{
        "id": "client123",
        "personal_info": "M. Dupont, 45 ans, salarié",
        "loan_amount": 8000,
        "loan_type": "personnel",
        "loan_desc": "Achat véhicule"
      }'
```

**Réponse (status 200)** :

```json
{
  "status": "pending",
  "message": "Veuillez soumettre un chèque de banque"
}
```

### Requête de prêt avec chèque valide

```bash
curl -X POST http://localhost:5000/loan \
  -H "Content-Type: application/json" \
  -d '{
        "id": "client123",
        "personal_info": "M. Dupont, 45 ans, salarié",
        "loan_amount": 8000,
        "loan_type": "personnel",
        "loan_desc": "Achat véhicule",
        "check": "valid"
      }'
```

**Réponse (status 200)** :

```json
{
  "status": "approved",
  "message": "Prêt approuvé et fonds transférés"
}
```

---

## 4. Arrêt des services

Pour arrêter et supprimer les conteneurs :

```bash
docker compose down
```

---

**Bon tests et bonne utilisation !**

