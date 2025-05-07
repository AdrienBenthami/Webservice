#!/usr/bin/env python3
"""
Application compagnon pour la gestion des demandes de prêt.
Orchestre les appels aux microservices et supporte le workflow asynchrone pour le chèque.
"""
from flask import Flask, request, jsonify
import requests
import grpc
import uuid
from xml.etree import ElementTree as ET
from ms_montantmax import montantmax_pb2, montantmax_pb2_grpc

app = Flask(__name__)

# Config des microservices
MS_MONTANTMAX_ADDRESS = 'localhost:50051'
MS_PROFILRISQUE_URL  = 'http://localhost:5001/graphql'
MS_BANQUE_URL         = 'http://localhost:5002/'   # SOAP async
MS_FOURNISSEUR_URL    = 'http://localhost:5003/fundTransfers'

# Stockage en mémoire des demandes (pour tests/demo)
_loans = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/loan', methods=['POST'])
def loan_request():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "reason": "Données de requête manquantes"}), 400

    client_id     = data.get("id")
    personal_info = data.get("personal_info")
    loan_amount   = data.get("loan_amount")
    if client_id is None or personal_info is None or loan_amount is None:
        return jsonify({"status": "error", "reason": "Paramètres requis manquants"}), 400

    # Montant en float
    try:
        loan_amount = float(loan_amount)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "reason": "Le montant doit être un nombre"}), 400

    # 1. Vérification gRPC MontantMax
    try:
        channel = grpc.insecure_channel(MS_MONTANTMAX_ADDRESS)
        stub    = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
        resp    = stub.CheckLoan(montantmax_pb2.LoanRequest(loan_amount=loan_amount))
    except Exception:
        return jsonify({"status": "error", "reason": "Erreur vérification montant"}), 500

    if not resp.allowed:
        return jsonify({"status": "refused", "reason": resp.message}), 400

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
    except Exception:
        return jsonify({"status": "error", "reason": "Erreur profil risque"}), 500

    if risk == 'elevé' and loan_amount >= 20000:
        return jsonify({"status": "refused", "reason": "Risque trop élevé"}), 400

    # 3. SubmitChequeRequest (asynchrone) → on récupère request_id
    soap = f'''<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <SubmitChequeRequest xmlns="ms.banque.async"/>
  </soapenv:Body>
</soapenv:Envelope>'''
    try:
        headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
        r = requests.post(MS_BANQUE_URL, data=soap, headers=headers, timeout=5)
        tree = ET.fromstring(r.content)
        ns   = {'soap11env': 'http://schemas.xmlsoap.org/soap/envelope/',
                'tns':       'ms.banque.async'}
        req_id = tree.findtext('.//tns:SubmitChequeRequestResult', namespaces=ns)
    except Exception:
        return jsonify({"status": "error", "reason": "Erreur dépôt chèque"}), 500

    # On stocke l'état initial
    _loans[req_id] = {
        'client_id':   client_id,
        'loan_amount': loan_amount,
        'status':      'pending'
    }

    return jsonify({
        "status":     "pending",
        "request_id": req_id,
        "message":    "Veuillez déposer votre chèque en utilisant cet ID"
    }), 200

@app.route('/loan/status/<request_id>', methods=['GET'])
def loan_status(request_id):
    entry = _loans.get(request_id)
    if not entry:
        return jsonify({"status": "error", "reason": "ID inconnu"}), 404

    if entry['status'] == 'pending':
        return jsonify({"status": "pending"}), 200

    # état 'done'
    verdict = entry.get('verdict', '')
    if verdict == 'Chèque validé':
        return jsonify({"status": "approved", "message": "Prêt approuvé et fonds transférés"}), 200
    else:
        return jsonify({"status": "refused", "reason": "Chèque invalide"}), 400

@app.route('/loan/callback', methods=['POST'])
def loan_callback():
    # Point de callback SOAP asynchrone
    content = request.data
    tree    = ET.fromstring(content)
    # On extrait simplement les balises <request_id> et <verdict>
    req_id  = tree.findtext('.//request_id')
    verdict = tree.findtext('.//verdict')

    entry = _loans.get(req_id)
    if not entry:
        return '', 404

    entry['status']  = 'done'
    entry['verdict'] = verdict or ''

    # Si validé, on appelle MS_FOURNISSEUR pour débloquer les fonds
    if verdict == 'Chèque validé':
        requests.post(
          MS_FOURNISSEUR_URL,
          json={'loan_amount': entry['loan_amount'], 'client_id': entry['client_id']},
          timeout=5
        )
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
