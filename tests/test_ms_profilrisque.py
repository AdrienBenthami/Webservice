import pytest
from ms_profilrisque.server import app

GRAPHQL_QUERY = '''
query($loanAmount: Float!, $clientInfo: String!) {
  riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo)
}
'''

@pytest.fixture
def client():
    with app.test_client() as c:
        yield c

def test_risk_profile_acceptable(client):
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"loanAmount": 1000, "clientInfo": "Test"}
    }
    rv = client.post('/graphql', json=payload)
    assert rv.status_code == 200
    assert rv.get_json()['riskProfile'] == 'acceptable'

def test_risk_profile_eleve(client):
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"loanAmount": 25000, "clientInfo": "Test"}
    }
    rv = client.post('/graphql', json=payload)
    assert rv.status_code == 200
    assert rv.get_json()['riskProfile'] == 'elevé'
