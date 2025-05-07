# Mini-Rapport : Application de gestion de prêt

## 1. Lien vers le dépôt

* [https://github.com/AdrienBenthami/Webservice.git](https://github.com/AdrienBenthami/Webservice.git)

## 2. Fiche d'auto-évaluation

| Critère                                                             | Points attribués | Points max |
| ------------------------------------------------------------------- | ---------------: | ---------: |
| Conception du workflow avec pools et interactions entre partenaires |                5 |         15 |
| Utilisation de gateways (OR, AND ou XOR)                            |               15 |         15 |
| Requête REST                                                        |               30 |         30 |
| Requête SOAP                                                        |               30 |         30 |
| Requête gRPC                                                        |               20 |         20 |
| Requête GraphQL                                                     |               20 |         20 |
| Tests et documentation des API                                      |               30 |         30 |
| Procédures correctes et exécution complète                          |               40 |         40 |
| Déploiement et gestion des microservices (optionnel)                |               50 |         50 |
| **Total**                                                           |              240 |        250 |

> **Note** : +50 points optionnels obtenus grâce à l’orchestration via Docker Compose et healthchecks.

## 3. How to install

### Prérequis

* **Docker** & **Docker Compose**
* **Python 3.10+** (hors conteneur, facultatif)
* **Redis** (géré via Docker, facultatif)
* **jq** (optionnel pour formater le JSON)

### Étapes d’installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/AdrienBenthami/Webservice.git
cd Webservice

# 2. Démarrer tous les services en conteneurs
docker compose up --build -d

# 3. Vérifier que tout est sain
docker compose ps  # chaque service doit être en état 'healthy'
```

## 4. How to use

1. **Créer une demande de prêt**

   ```bash
   curl -s -X POST http://localhost:5000/loan \
     -H "Content-Type: application/json" \
     -d '{"id":"client1","personal_info":"M. Dupont","loan_amount":8000}' | jq
   ```

   ![Création de la demande](images/screenshot_loan_request.png)

2. **Vérifier le statut**

   ```bash
   curl -s http://localhost:5000/loan/status/<request_id> | jq
   ```

   ![Statut de la demande](images/screenshot_status.png)

3. **Consulter l’historique des appels**

   ```bash
   curl -s http://localhost:5000/loan/history/<request_id> | jq
   ```

   ![Historique des appels](images/screenshot_history.png)

4. **Soumettre la validation du chèque**

   ```bash
   curl -s -X POST http://localhost:5000/loan/callback \
     -H "Content-Type: text/xml" \
     --data '<?xml version="1.0"?>\
   <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\
     <soapenv:Body>\
       <ChequeStatusResponse>\
         <request_id><request_id></request_id>\
         <status>done</status>\
         <verdict>Chèque validé</verdict>\
       </ChequeStatusResponse>\
     </soapenv:Body>\
   </soapenv:Envelope>'
   ```

   ![Callback SOAP](images/screenshot_callback.png)

5. **Vérifier le statut final**

   ```bash
   curl -s http://localhost:5000/loan/status/<request_id> | jq
   ```

   ![Statut final](images/screenshot_final.png)

*Remarque : Remplacez `<request_id>` par l’identifiant retourné lors de la création de la demande.*
