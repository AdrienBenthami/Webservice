# Documentation Complète des Tests Unitaires et d’Intégration

Ce document décrit en détail chaque cas de test, avec son objectif, sa configuration, les étapes d’exécution et les assertions.

## Table des Matières

1. [Configuration de l’environnement de test](#configuration-de-lenvironnement-de-test)
2. [Tests de `ms_montantmax` (gRPC)](#tests-de-ms_montantmax-grpc)
3. [Tests de `ms_profilrisque` (GraphQL)](#tests-de-ms_profilrisque-graphql)
4. [Tests de `ms_banque` (SOAP)](#tests-de-ms_banque-soap)
5. [Tests de `ms_fournisseur` (REST)](#tests-de-ms_fournisseur-rest)
6. [Tests de l’application Flask (orchestration)](#tests-de-lapplication-flask-orchestration)

---

## Configuration de l’environnement de test

* **Framework** : pytest
* **Fichiers de config** :

  * `pytest.ini` (chemins, options)
  * `conftest.py` (ajout de `src/` et `src/ms_montantmax` au `PYTHONPATH`)
* **Commande** :

  ```bash
  pytest -q
  ```
* **Fixtures globales** :

  * `service` pour `ms_montantmax`.
  * `client` pour les applications Flask.
  * `flush_cache` pour vider le dictionnaire avant/après `ms_banque`.
  * `mock_services` pour stubber gRPC et `requests.post` dans `test_app.py`.

---

## Tests de ms\_montantmax (gRPC)

**Fichier** : `tests/test_ms_montantmax.py`

#### Objectif

Vérifier la méthode `CheckLoan` du service gRPC, qui doit :

* **Retourner autorisé** (`allowed=True`) si `loan_amount <= 50000`.
* **Retourner refusé** (`allowed=False`) si `loan_amount > 50000`.

#### Détail des tests

1. **test\_checkloan\_within\_limit**

   * **Setup** :

     ```python
     req = LoanRequest(loan_amount=1000)
     ```
   * **Execution** :

     ```python
     resp = service.CheckLoan(req, None)
     ```
   * **Assertions** :

     ```python
     assert resp.allowed is True
     assert "Demande acceptée" in resp.message
     ```

2. **test\_checkloan\_above\_limit**

   * **Setup** :

     ```python
     req = LoanRequest(loan_amount=60000)
     ```
   * **Execution** : idem
   * **Assertions** :

     ```python
     assert resp.allowed is False
     assert "Montant trop élevé" in resp.message
     ```

---

## Tests de ms\_profilrisque (GraphQL)

**Fichier** : `tests/test_ms_profilrisque.py`

#### Objectif

S’assurer que la requête GraphQL `riskProfile` renvoie :

* **"acceptable"** pour un montant < 20000.
* **"élevé"** pour un montant ≥ 20000.

#### Détail des tests

1. **test\_risk\_profile\_acceptable**

   * **Payload** :

     ```json
     { "query": GRAPHQL_QUERY,
       "variables": {"loanAmount":1000, "clientInfo":"Test"} }
     ```
   * **Requête** :

     ```python
     rv = client.post('/graphql', json=payload)
     ```
   * **Assertions** :

     ```python
     assert rv.status_code == 200
     assert rv.get_json()['riskProfile'] == 'acceptable'
     ```

2. **test\_risk\_profile\_eleve**

   * **Payload** : montant = 25000
   * **Assertions** : réponse `élevé`

---

## Tests de ms\_banque (SOAP)

**Fichier** : `tests/test_ms_banque.py`

#### Objectif

Valider le workflow asynchrone : soumission de chèque, consultation avant/après dépôt, upload du chèque.

#### Setup

* **Skip** des tests si Python ≥ 3.11.
* **Fixtures** :

  * `flush_redis` pour nettoyer Redis.
  * `client` pour instancier `WsgiApplication(application)`.

#### test\_submit\_and\_get\_and\_upload\_and\_get

**Étapes** :

1. **SubmitChequeRequest**

   * Envoi d’une enveloppe SOAP `<SubmitChequeRequest/>`.
   * Extraction de `request_id` via XPath.
   * **Assertion** : `request_id` non vide.
2. **GetChequeStatus** (avant upload)

   * Envoi `<GetChequeStatus>` pour `request_id`.
   * **Assertion** : `<status>pending</status>`.
3. **UploadCheque**

   * Envoi `<UploadCheque>` avec `cheque='valid'`.
   * **Assertion** : `status_code == 200`.
4. **GetChequeStatus** (après upload)

   * Nouvelle requête `GetChequeStatus`.
   * **Assertions** :

     ```xml
     <status>done</status>
     <verdict>Chèque validé</verdict>
     ```

---

## Tests de ms\_fournisseur (REST)

**Fichier** : `tests/test_ms_fournisseur.py`

#### Objectif

Vérifier la création et la consultation des transferts de fonds.

#### Fixtures

* `client` : `app.test_client()`.

#### Tests

1. **test\_health**

   * **Requête** : GET `/health`
   * **Assertion** : 200, réponse `{"status":"ok"}`.
2. **test\_create\_fund\_transfer**

   * **Payload** : `{ "loan_amount":12345, "client_id":"clientX" }`
   * **Requête** : POST `/fundTransfers`
   * **Assertions** :

     ```python
     assert rv.status_code == 201
     data = rv.get_json()
     assert data['status']=='success'
     assert 'Fonds de 12345' in data['message']
     assert 'self' in data['links'] and 'status' in data['links']
     ```
3. **test\_get\_fund\_transfer\_status**

   * **Requête** : GET `/fundTransfers/1234/status`
   * **Assertion** : 200, `status=='completed'`.

---

## Tests de l’application Flask (Orchestration)

**Fichier** : `tests/test_app.py`

#### Objectif

Simuler le workflow complet en isolant les services externes via des mocks.

#### Fixtures & Mocks

* `@pytest.fixture(autouse=True) mock_services(monkeypatch)` :

  * Mocks gRPC (`MontantMaxServiceStub`) et `requests.post` pour GraphQL, SOAP et REST.
* `@pytest.fixture client` : instancie `flask_app.test_client()`.

#### Tests détaillés

1. **test\_missing\_data**

   * **Action** : POST `/loan` sans JSON
   * **Assertion** : 400, `status=='error'`, raison "Données de requête manquantes".

2. **test\_invalid\_amount\_type**

   * **Action** : JSON `{"loan_amount":"abc"}`
   * **Assertion** : 400, `reason` commence par "Le montant doit être un nombre".

3. **test\_grpc\_refuse**

   * **Action** : prêt 60000
   * **Assertion** : 400, `status=='refused'`.

4. **test\_risk\_refusal**

   * **Action** : prêt 25000
   * **Assertion** : 400, `reason=='Risque trop élevé'`.

5. **test\_flow\_async\_success**

   * **Étape 1** : POST `/loan`→200, `status=='pending'`, capture `request_id`
   * **Étape 2** : GET `/loan/status/{id}`→200, `status=='pending'`
   * **Étape 3** : POST `/loan/callback` with valid SOAP→200
   * **Étape 4** : GET final→200, `status=='approved'`, message contient "fonds"

6. **test\_flow\_async\_invalid**

   * Même que précédent, mais callback avec verdict invalide→GET final→400, `status=='refused'`.

**Fin de la documentation des tests unitaires.**
