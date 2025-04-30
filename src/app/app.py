#!/usr/bin/env python3
"""
Application compagnon pour la gestion des demandes de prêt.
Elle orchestre les appels aux différents microservices :
  - MS MontantMax (gRPC) pour la vérification du montant.
  - MS ProfilRisque (GraphQL) pour l'analyse du profil de risque.
  - MS Banque (SOAP) pour la validation du chèque.
  - MS Fournisseur (REST) pour la demande de financement.
"""

from flask import Flask, request, jsonify
import requests
import grpc
from ms_montantmax import montantmax_pb2
from ms_montantmax import montantmax_pb2_grpc

app = Flask(__name__)

# Adresses et ports des microservices (à ajuster si besoin)
MS_MONTANTMAX_ADDRESS = 'localhost:50051'
MS_PROFILRISQUE_URL = 'http://localhost:5001/graphql'
MS_BANQUE_URL = 'http://localhost:5002/soap'
MS_FOURNISSEUR_URL = 'http://localhost:5003/fundTransfers'

@app.route('/loan', methods=['POST'])
def loan_request():
    """
    Traite la demande de prêt en exécutant successivement :
      1. Vérification du montant via MS MontantMax (gRPC).
      2. Analyse du profil de risque via MS ProfilRisque (GraphQL).
      3. Validation de l'existence d'un chèque.
      4. Validation du chèque via MS Banque (SOAP).
      5. Demande de fonds via MS Fournisseur (REST).
    """
    try:
        # Récupération et vérification des données de la requête
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "reason": "Données de requête manquantes"}), 400

        client_id     = data.get("id")
        personal_info = data.get("personal_info")
        loan_type     = data.get("loan_type")
        loan_amount   = data.get("loan_amount")
        loan_desc     = data.get("loan_desc")

        # Vérifier que les paramètres essentiels sont présents
        if client_id is None or personal_info is None or loan_amount is None:
            return jsonify({"status": "error", "reason": "Paramètres requis manquants"}), 400

        # Assurer que le montant est un nombre
        try:
            loan_amount = float(loan_amount)
        except (ValueError, TypeError):
            return jsonify({"status": "error", "reason": "Le montant doit être un nombre"}), 400

        # 1. Vérification du montant avec MS MontantMax via gRPC
        try:
            with grpc.insecure_channel(MS_MONTANTMAX_ADDRESS) as channel:
                stub = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
                grpc_request = montantmax_pb2.LoanRequest(loan_amount=loan_amount)
                grpc_response = stub.CheckLoan(grpc_request)
        except Exception as e:
            # Vous pouvez ajouter ici un log de l'exception si besoin
            return jsonify({"status": "error", "reason": "Erreur lors de la vérification du montant"}), 500

        # Si le montant est refusé par le service, on arrête ici
        if not grpc_response.allowed:
            return jsonify({"status": "refused", "reason": "Montant trop élevé"}), 400

        # 2. Vérification du profil de risque via MS ProfilRisque (GraphQL)
        query = '''
        query($loanAmount: Float!, $clientInfo: String!) {
          riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo)
        }
        '''
        variables = {"loanAmount": loan_amount, "clientInfo": personal_info}
        try:
            response = requests.post(MS_PROFILRISQUE_URL, json={'query': query, 'variables': variables}, timeout=5)
            risk_data = response.json()
        except Exception as e:
            return jsonify({"status": "error", "reason": "Erreur lors de la vérification du profil de risque"}), 500

        # Gestion d'éventuelles erreurs GraphQL
        if 'errors' in risk_data:
            return jsonify({"status": "error", "reason": "Erreur GraphQL : " + str(risk_data['errors'])}), 500

        # Extraction du profil de risque ; le service renvoie directement { "riskProfile": <valeur> }
        if 'riskProfile' not in risk_data:
            return jsonify({"status": "error", "reason": "Réponse GraphQL inattendue"}), 500

        risk = risk_data['riskProfile']
        # Refus si le profil est "elevé" et que le montant est supérieur ou égal à 20000
        if risk == "elevé" and loan_amount >= 20000:
            return jsonify({"status": "refused", "reason": "Risque trop élevé"}), 400

        # 3. Vérification de la présence du chèque
        check = data.get("check")
        if not check:
            return jsonify({"status": "pending", "message": "Veuillez soumettre un chèque de banque"}), 200

        # 4. Validation du chèque via MS Banque (SOAP)
        soap_payload = f"""<?xml version="1.0"?>
<Envelope>
  <Body>
    <ValidateCheck>
      <check>{check}</check>
    </ValidateCheck>
  </Body>
</Envelope>"""
        try:
            headers = {'Content-Type': 'text/xml'}
            soap_response = requests.post(MS_BANQUE_URL, data=soap_payload, headers=headers, timeout=5)
        except Exception as e:
            return jsonify({"status": "error", "reason": "Erreur lors de la validation du chèque"}), 500

        # Si la réponse contient "invalid" (insensible à la casse), le chèque est refusé
        if "invalid" in soap_response.text.lower():
            return jsonify({"status": "refused", "reason": "Chèque invalide"}), 400

        # 5. Demande de financement via MS Fournisseur (REST)
        try:
            fund_response = requests.post(
                MS_FOURNISSEUR_URL,
                json={"loan_amount": loan_amount, "client_id": client_id},
                timeout=5
            )
        except Exception as e:
            return jsonify({"status": "error", "reason": "Erreur lors de la demande de financement"}), 500

        if fund_response.status_code != 200:
            return jsonify({"status": "refused", "reason": "Problème de financement"}), 400

        # Retour final en cas de succès
        return jsonify({"status": "approved", "message": "Prêt approuvé et fonds transférés"}), 200

    except Exception as e:
        # Gestion globale des erreurs non prévues
        return jsonify({"status": "error", "reason": "Erreur interne du serveur : " + str(e)}), 500

if __name__ == '__main__':
    # Lancer l'application sur le port 5000
    app.run(port=5000)
