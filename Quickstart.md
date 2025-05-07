# Guide Quickstart

Ce guide rapide vous permet de démarrer et de tester l’application en moins de 5 minutes.

### Prérequis

- **Git**
- **Docker** & **Docker Compose**  
- **Curl**
- **jq** (fortement recommandé pour formater le JSON)  

### 1. Cloner le dépôt

```bash
git clone https://github.com/AdrienBenthami/Webservice.git
cd Webservice
```

### 2. Démarrer tous les services en conteneurs

```bash
docker compose up --build -d
```

### 3. Vérifier que tout est sain

```bash
docker compose ps
```

Assurez-vous que chaque service affiche un état `healthy`.

> **Astuce** : si vous n’avez pas `jq`, remplacez `| jq` par `| python3 -m json.tool`.

### 4. Tester un flux complet et récupérer l’historique

1. **Soumettre une demande** (pas de chèque pour l’instant) :

   ```bash
   curl -s -X POST http://localhost:5000/loan \
     -H "Content-Type: application/json" \
     -d '{"id":"client1","personal_info":"M. Dupont","loan_amount":8000}' \
   | jq
   ```

   *(ou `| python3 -m json.tool` si vous n’avez pas `jq`)*

2. **Consulter le statut** :

   ```bash
   curl -s http://localhost:5000/loan/status/<request_id> | jq
   ```

   *Devrait retourner* `pending`.

3. **Consulter l’historique** :

   ```bash
   curl -s http://localhost:5000/loan/history/<request_id> | jq
   ```

   *Vous verrez un tableau d’entrées horodatées décrivant chaque appel aux services.*

4. **Simuler dépôt du chèque** (par défaut, `ms_banque` renvoie `valid`) :

   ```bash
   curl -s -X POST http://localhost:5000/loan/callback \
     -H "Content-Type: text/xml" \
     --data '<?xml version="1.0"?>
   <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
     <soapenv:Body>
       <ChequeStatusResponse>
         <request_id><request_id></request_id>
         <status>done</status>
         <verdict>Chèque validé</verdict>
       </ChequeStatusResponse>
     </soapenv:Body>
   </soapenv:Envelope>'
   ```

   On pourra aussi interroger le WSDL :
   ```bash
   curl -s http://localhost:5002/?wsdl | head -n 20
   ```

5. **Vérifier le statut final** :

   ```bash
   curl -s http://localhost:5000/loan/status/<request_id> | jq
   ```

   *Vous devriez obtenir* `status":"approved"`.

6. **Vérifier l’historique mis à jour** :

   ```bash
   curl -s http://localhost:5000/loan/history/<request_id> | jq
   ```

   *Vous y trouverez notamment* `ms_banque callback` *et* `ms_fournisseur` *dans la trace.*

Félicitations ! Votre application de prêt fonctionne et vous disposez d’une traçabilité complète de chaque étape.
