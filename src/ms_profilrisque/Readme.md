Pour tester:
```sh
python server.py
```
Ou en docker :
```sh
docker build -t ms_profilrisque .
docker run -d -p 5001:5001 ms_profilrisque
```

Dans un autre terminal :
```sh
curl http://localhost:5001/health
```

```sh
curl -X POST -H "Content-Type: application/json" \
-d '{
      "query": "query($loanAmount: Float!, $clientInfo: String!){ riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo) }",
      "variables": {"loanAmount": 25000, "clientInfo": "Information client exemple"}
    }' \
http://localhost:5001/graphql

```

Réponse : hrg
```sh
{"riskProfile":"elev\u00e9"}
```