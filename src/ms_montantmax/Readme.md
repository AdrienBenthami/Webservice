Pour tester:
```sh
docker build -t ms_montantmax .
docker run -d -p 50051:50051 ms_montantmax

```

Dans un autre terminal :
```sh
grpcurl -plaintext -proto ms_montantmax/montantmax.proto -d '{"loan_amount": 30000}' localhost:50051 ms_montantmax.MontantMaxService/CheckLoan
```

Réponse : 
```sh
{
  "allowed": true,
  "message": "Demande acceptée"
}
```


Ou alors :
Dans un autre terminal :
```sh
grpcurl -plaintext -proto ms_montantmax/montantmax.proto -d '{"loan_amount": 60000}' localhost:50051 ms_montantmax.MontantMaxService/CheckLoan
```

Réponse : 
```sh
{
  "message": "Montant trop élevé"
}
```