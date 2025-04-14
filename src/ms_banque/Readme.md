Pour tester:
```sh
docker build -t ms_banque .
docker run -d -p 5002:5002 ms_banque
```

Dans un autre terminal :
```sh
curl -X POST -H "Content-Type: text/xml" \
-d '<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ValidateCheck xmlns="ms.banque">
      <check>valid</check>
    </ValidateCheck>
  </soap:Body>
</soap:Envelope>' \
http://localhost:5002
```

Réponse : 
```sh
<?xml version='1.0' encoding='UTF-8'?>
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="ms      .banque"><soap11env:Body><tns:ValidateCheckResponse><tns:ValidateCheckResult>Chèque validé</t      ns:ValidateCheckResult></tns:ValidateCheckResponse></soap11env:Body></soap11env:Envelope>
```