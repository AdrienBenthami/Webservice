from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuration de l'URL de Bonita et des identifiants
BONITA_URL = "http://localhost:8080/bonita"  # Modifier si nécessaire
USERNAME = "admin"  # Compte par défaut, à adapter
PASSWORD = "admin"  # Compte par défaut, à adapter

def login_bonita(session):
    """
    Authentifie la session auprès de Bonita.
    Note : la méthode d'authentification peut varier selon la version de Bonita.
    """
    login_url = f"{BONITA_URL}/loginservice"
    params = {
        "username": USERNAME,
        "password": PASSWORD,
        "redirect": "false"
    }
    # Effectue une requête GET pour s'authentifier. Bonita gère les sessions via les cookies.
    session.get(login_url, params=params)
    return session

@app.route('/start_process', methods=['POST'])
def start_process():
    """
    Démarre une instance de processus Bonita.
    Le JSON envoyé doit contenir l'identifiant du processus (process_def_id) et éventuellement d'autres variables.
    Exemple de payload :
    {
      "process_def_id": "12345",
      "variables": {
          "loan_amount": 30000,
          "customer_id": "CUST001"
      }
    }
    """
    data = request.get_json()
    process_def_id = data.get('process_def_id')
    variables = data.get('variables', {})  # Variables de processus

    session = requests.Session()
    session = login_bonita(session)

    # Construire l'URL pour démarrer le processus
    inst_url = f"{BONITA_URL}/API/bpm/process/{process_def_id}/instantiation"
    
    # Démarrer le processus en envoyant les variables (le format exact dépend de votre modèle Bonita)
    response = session.post(inst_url, json=variables)
    
    if response.status_code == 200:
        return jsonify({"result": "Processus démarré", "data": response.json()})
    else:
        return jsonify({"error": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
