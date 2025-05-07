# ms\_banque – Service SOAP Asynchrone de Validation de Chèque

Ce micro-service simule une banque :

* Il garde en mémoire une demande de chèque (état `pending`).
* Il permet de consulter ce statut (`pending` → `done`).
* Il reçoit le dépôt du chèque (`valid` ou `invalid`), passe l’état à `done` et stocke le verdict.

---

## Prérequis

* Python 3.10+
* Redis (local ou via Docker)
* curl (pour les tests)
* (Optionnel) xmllint pour formater la sortie XML

---

## Installation

1. Placez-vous dans `Webservice/src/ms_banque`
2. Créez et activez un environnement virtuel :

   ```
   python3 -m venv env
   source env/bin/activate
   ```
3. Installez les dépendances :

   ```
   pip install -r requirements.txt
   ```
4. Lancez Redis si nécessaire :

   ```
   docker run -d --name msb_redis -p 6379:6379 redis:6-alpine
   ```

---

## Démarrage du service

```
cd Webservice/src/ms_banque
python server.py
```

Le service écoute sur **[http://0.0.0.0:5002/](http://0.0.0.0:5002/)**.

---

## Tests manuels avec curl

Vous allez exécuter **4 étapes**, une par une. Copiez-collez tel quel.

### Étape 1 – SubmitChequeRequest

```
curl -X POST http://localhost:5002/ \
  -H "Content-Type: application/soap+xml; charset=utf-8" \
  --data '<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:asy="ms.banque.async"
                  xmlns:wsa="http://www.w3.org/2005/08/addressing">
  <soapenv:Header>
    <wsa:MessageID>uuid-1</wsa:MessageID>
    <wsa:ReplyTo><wsa:Address>http://localhost:9000/loan/callback</wsa:Address></wsa:ReplyTo>
  </soapenv:Header>
  <soapenv:Body>
    <asy:SubmitChequeRequest/>
  </soapenv:Body>
</soapenv:Envelope>'
```

**Réponse attendue**

```xml
<soap11env:Envelope …>
  <soap11env:Body>
    <tns:SubmitChequeRequestResponse>
      <tns:SubmitChequeRequestResult>YOUR_REQUEST_ID</tns:SubmitChequeRequestResult>
    </tns:SubmitChequeRequestResponse>
  </soap11env:Body>
</soap11env:Envelope>
```

Notez **YOUR\_REQUEST\_ID** (UUID).

---

### Étape 2 – GetChequeStatus (avant dépôt)

```
curl -X POST http://localhost:5002/ \
  -H "Content-Type: text/xml; charset=utf-8" \
  --data '<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:asy="ms.banque.async">
  <soapenv:Body>
    <asy:GetChequeStatus>
      <asy:request_id>YOUR_REQUEST_ID</asy:request_id>
    </asy:GetChequeStatus>
  </soapenv:Body>
</soapenv:Envelope>'
```

**Réponse attendue**

```xml
<soap11env:Envelope …>
  <soap11env:Body>
    <tns:GetChequeStatusResponse>
      <tns:GetChequeStatusResult>
        <tns:status>pending</tns:status>
        <tns:verdict/>
      </tns:GetChequeStatusResult>
    </tns:GetChequeStatusResponse>
  </soap11env:Body>
</soap11env:Envelope>
```

---

### Étape 3 – UploadCheque (dépôt du chèque)

```
curl -X POST http://localhost:5002/ \
  -H "Content-Type: text/xml; charset=utf-8" \
  --data '<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:asy="ms.banque.async">
  <soapenv:Body>
    <asy:UploadCheque>
      <asy:request_id>YOUR_REQUEST_ID</asy:request_id>
      <asy:cheque>valid</asy:cheque>
    </asy:UploadCheque>
  </soapenv:Body>
</soapenv:Envelope>'
```

**Réponse attendue**

```
HTTP/1.0 200 OK
```

---

### Étape 4 – GetChequeStatus (après dépôt)

```
curl -X POST http://localhost:5002/ \
  -H "Content-Type: text/xml; charset=utf-8" \
  --data '<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:asy="ms.banque.async">
  <soapenv:Body>
    <asy:GetChequeStatus>
      <asy:request_id>YOUR_REQUEST_ID</asy:request_id>
    </asy:GetChequeStatus>
  </soapenv:Body>
</soapenv:Envelope>'
```

**Réponse attendue**

```xml
<soap11env:Envelope …>
  <soap11env:Body>
    <tns:GetChequeStatusResponse>
      <tns:GetChequeStatusResult>
        <tns:status>done</tns:status>
        <tns:verdict>Chèque validé</tns:verdict>
      </tns:GetChequeStatusResult>
    </tns:GetChequeStatusResponse>
  </soap11env:Body>
</soap11env:Envelope>
```

---

### Cas « Chèque invalide »

Reprenez **étape 3** en mettant `<asy:cheque>invalid</asy:cheque>`, puis **étape 4** :
vous verrez `verdict=Chèque invalide`.

---

## Workflow détaillé

* **SubmitChequeRequest** : stocke `{status: pending, reply_to, relates_to}` en Redis + renvoie `request_id`
* **GetChequeStatus** : lit Redis et renvoie `status + verdict`
* **UploadCheque** : met à jour `{status: done, verdict}`, lance un callback SOAP vers `ReplyTo` (facultatif)

---

Vous disposez désormais d’un guide complet pour déployer et tester manuellement toutes les opérations de **ms\_banque**.
