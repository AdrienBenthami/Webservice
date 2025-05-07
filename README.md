## Fichier : README.md

# Application Compagnon – README détaillé

## Table des matières

1. [Présentation](#présentation)
2. [Architecture](#architecture)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Démarrage des microservices](#démarrage-des-microservices)
7. [Démarrage de l’application compagnon](#démarrage-de-lapplication-compagnon)
8. [Endpoints](#endpoints)
9. [Tests](#tests)
10. [Contribuer](#contribuer)
11. [Licence](#licence)

---

## Présentation

L’**Application Compagnon** orchestre un workflow de demande de prêt en interagissant avec plusieurs micro-services :

* **ms\_montantmax** (gRPC) : vérification du montant maximal autorisé.
* **ms\_profilrisque** (GraphQL) : évaluation du profil de risque client.
* **ms\_banque** (SOAP asynchrone) : validation du chèque de banque.
* **ms\_fournisseur** (REST) : libération et transfert des fonds.

Chaque service est containerisé et déployé via Docker Compose.

## Architecture

![Diagramme d’architecture](docs/architecture.png)

1. Le client envoie une requête POST `/loan` à l’app Flask.
2. L’app appelle le service gRPC **ms\_montantmax** pour vérifier le montant.
3. Si validé, elle interroge **ms\_profilrisque** via GraphQL.
4. Si le risque est acceptable, elle soumet un chèque à **ms\_banque** (SOAP async).
5. Une fois le callback reçu, elle interroge **ms\_fournisseur** pour le transfert.

Le dossier `docs/` contient des diagrammes UML détaillés.

## Prérequis

* **Docker** & **Docker Compose**
* **Python 3.10+** (pour exécution locale hors conteneur)
* **Redis** (utilisé par `ms_banque`, géré via Docker)

## Installation

1. Cloner ce dépôt :

   ```bash
   git clone https://github.com/AdrienBenthami/Webservice.git
   cd Webservice
   ```
2. (Optionnel) Créer un environnement virtuel pour tests locaux :

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r src/app/requirements.txt
   ```

## Configuration

* Le fichier `compose.yaml` expose tous les ports nécessaires :

  * 50051 (gRPC MontantMax)
  * 5001 (GraphQL ProfilRisque)
  * 5002 (SOAP Banque)
  * 5003 (REST Fournisseur)
  * 5000 (Flask App)
* Les URLs de chaque service sont configurées dans `src/app/app.py` via les variables :

  ```python
  MS_MONTANTMAX_ADDRESS = 'localhost:50051'
  MS_PROFILRISQUE_URL  = 'http://localhost:5001/graphql'
  MS_BANQUE_URL         = 'http://localhost:5002/'
  MS_FOURNISSEUR_URL    = 'http://localhost:5003/fundTransfers'
  ```

## Démarrage des microservices

Depuis la racine du projet :

```bash
docker compose up --build -d
```

Vérifiez l’état des services :

```bash
docker compose ps
```

## Démarrage de l’application compagnon

Si vous utilisez Docker Compose, le service `app` démarre automatiquement.

Pour un lancement local sans conteneurs :

```bash
cd src/app
source venv/bin/activate  # si utilisé
pip install -r requirements.txt
python app.py
```

L’application écoute sur le port **5000**.

## Endpoints

### Application Flask (/app)

| Méthode | Endpoint                    | Description                                   |
| ------- | --------------------------- | --------------------------------------------- |
| GET     | `/health`                   | Vérifie que l’app est opérationnelle.         |
| POST    | `/loan`                     | Soumettre une demande de prêt.                |
| GET     | `/loan/status/{request_id}` | Récupérer le statut de la demande.            |
| POST    | `/loan/callback`            | Point de callback SOAP interne (automatique). |

### ms\_fournisseur (REST)

| Méthode | Endpoint                     | Description                   |
| ------- | ---------------------------- | ----------------------------- |
| GET     | `/health`                    | Healthcheck.                  |
| POST    | `/fundTransfers`             | Créer un transfert de fonds.  |
| GET     | `/fundTransfers/{id}/status` | Statut du transfert de fonds. |

### ms\_profilrisque (GraphQL)

* Endpoint unique : `/graphql`
* Requête :

  ```graphql
  query($loanAmount: Float!, $clientInfo: String!) {
    riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo)
  }
  ```

### ms\_montantmax (gRPC)

* Service : `ms_montantmax.MontantMaxService`
* Méthode : `CheckLoan(LoanRequest) returns LoanResponse`
* Exemple de commande `grpcurl` dans `src/ms_montantmax/Readme.md`.

## Tests

Exécuter l’ensemble des tests unitaires et d’intégration :

```bash
pytest -q
```

Le fichier `pytest.ini` est préconfiguré pour le dossier `tests/`.



