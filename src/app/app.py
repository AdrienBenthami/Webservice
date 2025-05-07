#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application compagnon pour la gestion des demandes de prêt.
Orchestre les appels aux microservices et supporte le workflow asynchrone pour le chèque.
Ajout : documentation Swagger via Flasgger.
"""
import os
import uuid
import datetime
from xml.etree import ElementTree as ET

from flask import Flask, request, jsonify
from flasgger import Swagger
import requests
import grpc
from ms_montantmax import montantmax_pb2, montantmax_pb2_grpc

# ------------------------------------------------------------------------------
# Configuration de l’application et de Swagger
# ------------------------------------------------------------------------------
app = Flask(__name__)

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Loan Orchestration API",
        "description": "API REST orchestrant le workflow de demande de prêt "
                       "et les appels aux micro‑services (gRPC, GraphQL, SOAP, REST).",
        "version": "1.0.0"
    },
    "basePath": "/",
}
swagger = Swagger(app, template=swagger_template)

# ------------------------------------------------------------------------------
# Variables d’environnement / adresses des micro‑services
# ------------------------------------------------------------------------------
MS_MONTANTMAX_ADDRESS = os.getenv('MS_MONTANTMAX_ADDRESS', 'ms_montantmax:50051')
MS_PROFILRISQUE_URL   = os.getenv('MS_PROFILRISQUE_URL',  'http://ms_profilrisque:5001/graphql')
MS_BANQUE_URL         = os.getenv('MS_BANQUE_URL',        'http://ms_banque:5002/')
MS_FOURNISSEUR_URL    = os.getenv('MS_FOURNISSEUR_URL',   'http://ms_fournisseur:5003/fundTransfers')

# Stockage en mémoire des demandes (pour démo/tests)
_loans: dict[str, dict] = {}

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    """
    Healthcheck de l’application.
    ---
    tags:
      - misc
    responses:
      200:
        description: Service opérationnel
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
    """
    return jsonify({"status": "ok"}), 200


@app.route('/loan', methods=['POST'])
def loan_request():
    """
    Soumettre une demande de prêt.

    ---
    tags:
      - loan
    consumes:
      - application/json
    parameters:
      - in: body
        name: payload
        description: Informations sur la demande de prêt
        required: true
        schema:
          type: object
          required: [id, personal_info, loan_amount]
          properties:
            id:
              type: string
              example: client1
            personal_info:
              type: string
              example: "M. Dupont"
            loan_amount:
              type: number
              format: float
              example: 8000
    responses:
      200:
        description: Demande acceptée et en attente du chèque
        schema:
          $ref: '#/definitions/PendingLoanResponse'
      400:
        description: Refus ou erreur de validation
        schema:
          $ref: '#/definitions/ErrorResponse'
    definitions:
      PendingLoanResponse:
        type: object
        properties:
          status:
            type: string
            example: pending
          request_id:
            type: string
            example: "f4a5e244‑c3d0‑433e‑9a1e‑89456b13e8d1"
          message:
            type: string
            example: Veuillez déposer votre chèque en utilisant cet ID
      ErrorResponse:
        type: object
        properties:
          status:
            type: string
            example: error
          reason:
            type: string
            example: Paramètres requis manquants
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "reason": "Données de requête manquantes"}), 400

    client_id     = data.get("id")
    personal_info = data.get("personal_info")
    loan_amount   = data.get("loan_amount")
    if client_id is None or personal_info is None or loan_amount is None:
        return jsonify({"status": "error", "reason": "Paramètres requis manquants"}), 400

    # Validation du montant
    try:
        loan_amount = float(loan_amount)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "reason": "Le montant doit être un nombre"}), 400

    # Initialiser l'historique
    history = [{
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "client",
        "request": {"id": client_id, "personal_info": personal_info, "loan_amount": loan_amount}
    }]

    # 1. Vérification gRPC MontantMax
    try:
        channel = grpc.insecure_channel(MS_MONTANTMAX_ADDRESS)
        stub    = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
        resp    = stub.CheckLoan(montantmax_pb2.LoanRequest(loan_amount=loan_amount))
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_montantmax",
            "request": {"loan_amount": loan_amount},
            "response": {"allowed": resp.allowed, "message": resp.message}
        })
    except Exception:
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_montantmax",
            "error": "Erreur vérification montant"
        })
        return jsonify({"status": "error", "reason": "Erreur vérification montant"}), 500

    if not resp.allowed:
        req_id = str(uuid.uuid4())
        _loans[req_id] = {"client_id": client_id, "loan_amount": loan_amount,
                          "status": "refused", "history": history}
        return jsonify({"status": "refused", "reason": resp.message,
                        "request_id": req_id}), 400

    # 2. Vérification profil de risque (GraphQL)
    query = '''
      query($loanAmount: Float!, $clientInfo: String!) {
        riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo)
      }
    '''
    try:
        gql = requests.post(
            MS_PROFILRISQUE_URL,
            json={'query': query, 'variables': {'loanAmount': loan_amount, 'clientInfo': personal_info}},
            timeout=5
        )
        risk = gql.json().get('riskProfile')
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_profilrisque",
            "request": {"loanAmount": loan_amount, "clientInfo": personal_info},
            "response": {"riskProfile": risk}
        })
    except Exception:
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_profilrisque",
            "error": "Erreur profil risque"
        })
        return jsonify({"status": "error", "reason": "Erreur profil risque"}), 500

    if risk == 'elevé' and loan_amount >= 20000:
        req_id = str(uuid.uuid4())
        _loans[req_id] = {"client_id": client_id, "loan_amount": loan_amount,
                          "status": "refused", "history": history}
        return jsonify({"status": "refused", "reason": "Risque trop élevé",
                        "request_id": req_id}), 400

    # 3. SubmitChequeRequest (SOAP async)
    soap = '''<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <SubmitChequeRequest xmlns="ms.banque.async"/>
  </soapenv:Body>
</soapenv:Envelope>'''
    try:
        r = requests.post(MS_BANQUE_URL,
                          data=soap,
                          headers={'Content-Type': 'application/soap+xml; charset=utf-8'},
                          timeout=5)
        tree = ET.fromstring(r.content)
        ns   = {'tns': 'ms.banque.async'}
        req_id = tree.findtext('.//tns:SubmitChequeRequestResult', namespaces=ns)
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_banque (SubmitChequeRequest)",
            "response": {"request_id": req_id}
        })
    except Exception:
        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "ms_banque (SubmitChequeRequest)",
            "error": "Erreur dépôt chèque"
        })
        return jsonify({"status": "error", "reason": "Erreur dépôt chèque"}), 500

    _loans[req_id] = {
        "client_id": client_id,
        "loan_amount": loan_amount,
        "status": "pending",
        "history": history
    }
    return jsonify({
        "status": "pending",
        "request_id": req_id,
        "message": "Veuillez déposer votre chèque en utilisant cet ID"
    }), 200


@app.route('/loan/status/<request_id>', methods=['GET'])
def loan_status(request_id):
    """
    Obtenir le statut d’une demande de prêt.
    ---
    tags:
      - loan
    parameters:
      - in: path
        name: request_id
        type: string
        required: true
        description: Identifiant de la demande de prêt
    responses:
      200:
        description: Statut actuel de la demande
      400:
        description: Demande refusée
      404:
        description: ID inconnu
    """
    entry = _loans.get(request_id)
    if not entry:
        return jsonify({"status": "error", "reason": "ID inconnu"}), 404

    if entry['status'] == 'pending':
        return jsonify({"status": "pending"}), 200

    verdict = entry.get('verdict', '')
    if verdict == 'Chèque validé':
        return jsonify({"status": "approved",
                        "message": "Prêt approuvé et fonds transférés"}), 200
    return jsonify({"status": "refused",
                    "reason": "Chèque invalide"}), 400


@app.route('/loan/callback', methods=['POST'])
def loan_callback():
    """
    Point de callback SOAP pour la banque.
    ---
    tags:
      - loan
    consumes:
      - text/xml
    parameters:
      - in: body
        name: callback
        required: true
        description: Enveloppe SOAP ChequeStatusResponse
        schema:
          type: string
    responses:
      200:
        description: Callback traité
      404:
        description: request_id inconnu
    """
    tree = ET.fromstring(request.data)
    req_id  = tree.findtext('.//request_id')
    verdict = tree.findtext('.//verdict')

    entry = _loans.get(req_id)
    if not entry:
        return '', 404

    entry['status']  = 'done'
    entry['verdict'] = verdict or ''
    entry['history'].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "ms_banque callback",
        "response": {"request_id": req_id, "verdict": verdict}
    })

    # Appel REST ms_fournisseur si le chèque est validé
    if verdict == 'Chèque validé':
        try:
            resp = requests.post(
                MS_FOURNISSEUR_URL,
                json={'loan_amount': entry['loan_amount'], 'client_id': entry['client_id']},
                timeout=5
            )
            entry['history'].append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "service": "ms_fournisseur",
                "request": {"loan_amount": entry['loan_amount'],
                            "client_id": entry['client_id']},
                "response": {"status_code": resp.status_code, "json": resp.json()}
            })
        except Exception:
            entry['history'].append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "service": "ms_fournisseur",
                "error": "Erreur transfert fonds"
            })
    return '', 200


@app.route('/loan/history/<request_id>', methods=['GET'])
def loan_history(request_id):
    """
    Récupérer l’historique détaillé des appels d’un prêt.
    ---
    tags:
      - loan
    parameters:
      - in: path
        name: request_id
        required: true
        type: string
    responses:
      200:
        description: Historique renvoyé
      404:
        description: ID inconnu
    """
    entry = _loans.get(request_id)
    if not entry:
        return jsonify({"status": "error", "reason": "ID inconnu"}), 404
    return jsonify({"request_id": request_id,
                    "history": entry.get("history", [])}), 200


# ------------------------------------------------------------------------------
# Lancement de l’application
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # /apidocs → UI Swagger
    app.run(host='0.0.0.0', port=5000)
