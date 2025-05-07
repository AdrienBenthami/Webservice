#!/usr/bin/env python3
"""
Application compagnon pour la gestion des demandes de prêt.
Orchestre les appels aux microservices et supporte le workflow asynchrone pour le chèque.
Ajout de la traçabilité des appels aux microservices.
"""
import os
from flask import Flask, request, jsonify
import requests
import grpc
import uuid
from xml.etree import ElementTree as ET
from ms_montantmax import montantmax_pb2, montantmax_pb2_grpc
import datetime

app = Flask(__name__)

# Config des microservices
MS_MONTANTMAX_ADDRESS = os.getenv('MS_MONTANTMAX_ADDRESS', 'ms_montantmax:50051')
MS_PROFILRISQUE_URL  = os.getenv('MS_PROFILRISQUE_URL',  'http://ms_profilrisque:5001/graphql')
MS_BANQUE_URL         = os.getenv('MS_BANQUE_URL',         'http://ms_banque:5002/')
MS_FOURNISSEUR_URL    = os.getenv('MS_FOURNISSEUR_URL',    'http://ms_fournisseur:5003/fundTransfers')

# Stockage en mémoire des demandes (pour tests/demo), incluant l'historique
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

    # Initialiser l'historique
    history = []
    now = datetime.datetime.utcnow().isoformat()
    history.append({
        "timestamp": now,
        "service": "client",
        "request": {"id": client_id, "personal_info": personal_info, "loan_amount": loan_amount}
    })

    # 1. Vérification gRPC MontantMax
    try:
        channel = grpc.insecure_channel(MS_MONTANTMAX_ADDRESS)
        stub    = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
        resp    = stub.CheckLoan(montantmax_pb2.LoanRequest(loan_amount=loan_amount))
        now = datetime.datetime.utcnow().isoformat()
        history.append({
            "timestamp": now,
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
        # Enregistrer l'historique même en cas de refus
        req_id = str(uuid.uuid4())
        _loans[req_id] = {"client_id": client_id, "loan_amount": loan_amount, "status": "refused", "history": history}
        return jsonify({"status": "refused", "reason": resp.message, "request_id": req_id}), 400

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
        now = datetime.datetime.utcnow().isoformat()
        history.append({
            "timestamp": now,
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
        _loans[req_id] = {"client_id": client_id, "loan_amount": loan_amount, "status": "refused", "history": history}
        return jsonify({"status": "refused", "reason": "Risque trop élevé", "request_id": req_id}), 400

    # 3. SubmitChequeRequest (asynchrone)
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
        now = datetime.datetime.utcnow().isoformat()
        history.append({
            "timestamp": now,
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

    # Stocker l'état initial
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
    entry = _loans.get(request_id)
    if not entry:
        return jsonify({"status": "error", "reason": "ID inconnu"}), 404

    if entry['status'] == 'pending':
        return jsonify({"status": "pending"}), 200

    verdict = entry.get('verdict', '')
    if verdict == 'Chèque validé':
        return jsonify({"status": "approved", "message": "Prêt approuvé et fonds transférés"}), 200
    else:
        return jsonify({"status": "refused", "reason": "Chèque invalide"}), 400

@app.route('/loan/callback', methods=['POST'])
def loan_callback():
    content = request.data
    tree    = ET.fromstring(content)
    req_id  = tree.findtext('.//request_id')
    verdict = tree.findtext('.//verdict')

    entry = _loans.get(req_id)
    if not entry:
        return '', 404

    now = datetime.datetime.utcnow().isoformat()
    # Mettre à jour le statut et l'historique
    entry['status']  = 'done'
    entry['verdict'] = verdict or ''
    entry['history'].append({
        "timestamp": now,
        "service": "ms_banque callback",
        "response": {"request_id": req_id, "verdict": verdict}
    })

    # Appel MS Fournisseur si chèque validé
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
                "request": {"loan_amount": entry['loan_amount'], "client_id": entry['client_id']},
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
    entry = _loans.get(request_id)
    if not entry:
        return jsonify({"status": "error", "reason": "ID inconnu"}), 404
    return jsonify({"request_id": request_id, "history": entry.get("history", [])}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
