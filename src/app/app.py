# src/app/app.py
from flask import Flask, request, jsonify
import requests
import grpc
# Importez ici les stubs gRPC générés (après compilation du proto)
import montantmax_pb2
import montantmax_pb2_grpc

app = Flask(__name__)

# Adresses et ports des microservices (à ajuster)
MS_MONTANTMAX_ADDRESS = 'localhost:50051'
MS_PROFILRISQUE_URL = 'http://localhost:5001/graphql'
MS_BANQUE_URL = 'http://localhost:5002/soap'
MS_FOURNISSEUR_URL = 'http://localhost:5003/fund'

@app.route('/loan', methods=['POST'])
def loan_request():
    data = request.json
    client_id = data.get("id")
    personal_info = data.get("personal_info")
    loan_type = data.get("loan_type")
    loan_amount = data.get("loan_amount")
    loan_desc = data.get("loan_desc")
    
    # 1. Vérifier le montant avec MS MontantMax (gRPC)
    with grpc.insecure_channel(MS_MONTANTMAX_ADDRESS) as channel:
        stub = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
        grpc_request = montantmax_pb2.LoanRequest(loan_amount=loan_amount)
        grpc_response = stub.CheckLoan(grpc_request)
    if not grpc_response.allowed:
        return jsonify({"status": "refused", "reason": "Montant trop élevé"}), 400

    # 2. Vérifier le profil de risque via MS ProfilRisque (GraphQL)
    query = '''
    query($loanAmount: Float!, $clientInfo: String!) {
      riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo)
    }
    '''
    variables = {"loanAmount": loan_amount, "clientInfo": personal_info}
    response = requests.post(MS_PROFILRISQUE_URL, json={'query': query, 'variables': variables})
    risk_data = response.json()
    risk = risk_data['data']['riskProfile']
    if risk == "elevé" and loan_amount >= 20000:
        return jsonify({"status": "refused", "reason": "Risque trop élevé"}), 400

    # 3. Demander au client de soumettre un chèque
    # Ici, on suppose que le client envoie le chèque dans la même requête (pour simplifier)
    check = data.get("check")
    if not check:
        return jsonify({"status": "pending", "message": "Veuillez soumettre un chèque de banque"}), 200

    # 4. Valider le chèque via MS Banque (SOAP)
    soap_payload = f"""<?xml version="1.0"?>
    <Envelope>
      <Body>
        <ValidateCheck>
          <check>{check}</check>
        </ValidateCheck>
      </Body>
    </Envelope>"""
    headers = {'Content-Type': 'text/xml'}
    soap_response = requests.post(MS_BANQUE_URL, data=soap_payload, headers=headers)
    if "invalid" in soap_response.text:
        return jsonify({"status": "refused", "reason": "Chèque invalide"}), 400

    # 5. Demander les fonds via MS Fournisseur (REST)
    fund_response = requests.post(MS_FOURNISSEUR_URL, json={"loan_amount": loan_amount, "client_id": client_id})
    if fund_response.status_code != 200:
        return jsonify({"status": "refused", "reason": "Problème de financement"}), 400

    return jsonify({"status": "approved", "message": "Prêt approuvé et fonds transférés"}), 200

if __name__ == '__main__':
    app.run(port=5000)
