from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Endpoint pour créer un transfert de fonds (ressource : fundTransfers)
@app.route('/fundTransfers', methods=['POST'])
def create_fund_transfer():
    data = request.json
    loan_amount = data.get("loan_amount")
    client_id = data.get("client_id")
    # Dans une application réelle, on générerait un identifiant unique et on enregistrerait la demande.
    transfer_id = "1234"  # Exemple statique
    response = {
        "status": "success",
        "message": f"Fonds de {loan_amount} transférés pour le client {client_id}",
        "links": {
            "self": f"/fundTransfers/{transfer_id}",
            "status": f"/fundTransfers/{transfer_id}/status"
        }
    }
    return jsonify(response), 201

# Endpoint pour consulter l'état d'un transfert (simulation)
@app.route('/fundTransfers/<transfer_id>/status', methods=['GET'])
def get_fund_transfer_status(transfer_id):
    # Ici, on simule toujours un statut "completed"
    return jsonify({
        "transfer_id": transfer_id,
        "status": "completed"
    }), 200

# Endpoint dédié au healthcheck
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003)
