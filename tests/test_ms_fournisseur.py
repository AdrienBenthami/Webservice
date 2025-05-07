import pytest
from ms_fournisseur.server import app

@pytest.fixture
def client():
    with app.test_client() as c:
        yield c

def test_health(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    assert rv.get_json() == {"status": "ok"}

def test_create_fund_transfer(client):
    payload = {"loan_amount": 12345, "client_id": "clientX"}
    rv = client.post('/fundTransfers', json=payload)
    assert rv.status_code == 201
    j = rv.get_json()
    assert j["status"] == "success"
    assert "Fonds de 12345" in j["message"]
    assert "self" in j["links"] and "status" in j["links"]

def test_get_fund_transfer_status(client):
    rv = client.get('/fundTransfers/1234/status')
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "completed"
