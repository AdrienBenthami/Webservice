Pour tester:
```sh
python server.py
```
Ou en docker :
```sh
docker build -t ms_fournisseur .
docker run -d -p 5003:5003 ms_fournisseur
```

Dans un autre terminal :
```sh
curl http://localhost:5003/health
```

```sh
curl -X POST -H "Content-Type: application/json" \
  -d '{"loan_amount": 15000, "client_id": "client123"}' \
  http://localhost:5003/fundTransfers
```

Réponse : 
```sh
{
  "status": "success",
  "message": "Fonds de 15000 transférés pour le client client123"
}

```