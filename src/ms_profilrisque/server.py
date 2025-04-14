# src/ms_profilrisque/app.py
from flask import Flask, request, jsonify
from graphene import ObjectType, String, Schema, Float

class Query(ObjectType):
    riskProfile = String(loanAmount=Float(required=True), clientInfo=String(required=True))

    def resolve_riskProfile(root, info, loanAmount, clientInfo):
        # Implémentez ici la logique d'analyse du risque.
        # Par exemple, si le montant est élevé, on renvoie "elevé"
        if loanAmount >= 20000:
            return "elevé"
        else:
            return "acceptable"

schema = Schema(query=Query)

app = Flask(__name__)

@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()
    result = schema.execute(data.get("query"), variables=data.get("variables"))
    return jsonify(result.data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
