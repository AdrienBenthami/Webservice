# Guide Quickstart

Ce guide rapide vous permet de démarrer et de tester l’application en moins de 5 minutes.

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

### 4. Tester un flux complet

1. **Soumettre une demande** (pas de chèque pour l’instant) :

   ```bash
   curl -X POST http://localhost:5000/loan \
     -H "Content-Type: application/json" \
     -d '{"id":"client1","personal_info":"M. Dupont","loan_amount":8000}'
   ```

   * Vous obtiendrez un JSON avec `status":"pending"` et un `request_id`.

2. **Consulter le statut** :

   ```bash
   curl http://localhost:5000/loan/status/<request_id>
   ```

   * Devrait retourner `pending`.

3. **Simuler dépôt du chèque** (par défaut, `ms_banque` renvoie `valid`) :

   ```bash
   curl -X POST http://localhost:5000/loan/callback \
     -H "Content-Type: text/xml" \
     --data '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><ChequeStatusResponse><request_id>'<request_id>'</request_id><status>done</status><verdict>Chèque validé</verdict></ChequeStatusResponse></soapenv:Body></soapenv:Envelope>'
   ```

4. **Vérifier le statut final** :

   ```bash
   curl http://localhost:5000/loan/status/<request_id>
   ```

   * Vous devriez obtenir `status":"approved"`.

Félicitations ! Votre application de prêt fonctionne.