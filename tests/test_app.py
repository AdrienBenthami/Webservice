import pytest
from flask import json
import grpc
import requests
from app.app import app as flask_app
from ms_montantmax import montantmax_pb2, montantmax_pb2_grpc

# Dummy gRPC response
class DummyLoanResponse:
    def __init__(self, allowed, message):
        self.allowed = allowed
        self.message = message

class FakeStub:
    def __init__(self, _):
        pass
    def CheckLoan(self, request):
        # Approve amounts <=50000, refuse otherwise
        if request.loan_amount <= 50000:
            return DummyLoanResponse(True, "Demande acceptée")
        return DummyLoanResponse(False, "Montant trop élevé")

# Dummy HTTP responses for GraphQL, SOAP, and REST
class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="", ok=True):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json
    @property
    def ok(self):
        return self.status_code == 200

@pytest.fixture(autouse=True)
def mock_services(monkeypatch):
    # Mock gRPC channel and stub
    monkeypatch.setattr(grpc, 'insecure_channel', lambda addr: None)
    monkeypatch.setattr(montantmax_pb2_grpc, 'MontantMaxServiceStub', FakeStub)

    # Default GraphQL risk acceptable for amounts <20000, risk élevé otherwise
    def fake_post(url, **kwargs):
        if 'graphql' in url:
            amt = kwargs['json']['variables']['loanAmount']
            risk = 'elevé' if amt >= 20000 else 'acceptable'
            return DummyResponse(status_code=200, json_data={'riskProfile': risk})
        if 'soap' in url:
            body = kwargs.get('data', '')
            # if <check>valid</check> present, valid; else invalid
            return DummyResponse(status_code=200, text='<ValidateCheckResult>Chèque validé</ValidateCheckResult>')
        if 'fundTransfers' in url:
            return DummyResponse(status_code=200, json_data={'status': 'success'})
        return DummyResponse(status_code=404)
    monkeypatch.setattr(requests, 'post', fake_post)

@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c

# Test missing JSON data
def test_missing_data(client):
    resp = client.post('/loan')
    data = resp.get_json()
    assert resp.status_code == 400
    assert data['status'] == 'error'
    assert 'Données de requête manquantes' in data['reason']

# Test invalid loan_amount type
def test_invalid_amount_type(client):
    resp = client.post('/loan', json={'id': '1', 'personal_info': 'x', 'loan_amount': 'abc'})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data['status'] == 'error'
    assert 'Le montant doit être un nombre' in data['reason']

# Test amount too high by gRPC
def test_grpc_refuse(client):
    resp = client.post('/loan', json={'id': '1', 'personal_info': 'x', 'loan_amount': 60000})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data['status'] == 'refused'
    assert 'Montant trop élevé' in data['reason']

# Test risk refusal for high risk and high amount
def test_risk_refusal(client):
    resp = client.post('/loan', json={'id': '1', 'personal_info': 'x', 'loan_amount': 25000})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data['status'] == 'refused'
    assert 'Risque trop élevé' in data['reason']

# Test pending for missing check
def test_pending_no_check(client):
    resp = client.post('/loan', json={'id': '1', 'personal_info': 'x', 'loan_amount': 10000})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['status'] == 'pending'
    assert 'Veuillez soumettre un chèque' in data['message']

# Test invalid check
def test_invalid_check(client, mock_services, monkeypatch):
    # override SOAP to return invalid
    def fake_soap(url, **kwargs):
        return DummyResponse(status_code=200, text='invalid')
    monkeypatch.setattr(requests, 'post', fake_soap)
    payload = {'id': '1', 'personal_info': 'x', 'loan_amount': 10000, 'check': 'anything'}
    resp = client.post('/loan', json=payload)
    data = resp.get_json()
    assert resp.status_code == 400
    assert data['status'] == 'refused'
    assert 'Chèque invalide' in data['reason']

# Test successful flow
def test_success_flow(client):
    payload = {'id': '1', 'personal_info': 'x', 'loan_amount': 10000, 'check': 'valid'}
    resp = client.post('/loan', json=payload)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['status'] == 'approved'
    assert 'Prêt approuvé' in data['message']
