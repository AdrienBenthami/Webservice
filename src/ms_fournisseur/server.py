# src/ms_fournisseur/app.py
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.route('/fund', methods=['POST'])
def fund_request():
    data = request.json
    loan_amount = data.get("loan_amount")
    client_id = data.get("client_id")
    # Simuler le transfert des fonds
    return jsonify({
        "status": "success", 
        "message": f"Fonds de {loan_amount} transférés pour le client {client_id}"
    }), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003)
