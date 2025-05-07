import pytest
import grpc
from flask import json
from xml.etree import ElementTree as ET

from app.app import app as flask_app, MS_BANQUE_URL, MS_PROFILRISQUE_URL, MS_FOURNISSEUR_URL
from ms_montantmax import montantmax_pb2_grpc

# Stub pour gRPC MontantMax
class DummyLoanResponse:
    def __init__(self, allowed, message):
        self.allowed = allowed
        self.message = message

class FakeMontantStub:
    def __init__(self, _):
        pass

    def CheckLoan(self, request):
        if request.loan_amount <= 50000:
            return DummyLoanResponse(True, "Demande acceptée")
        return DummyLoanResponse(False, "Montant trop élevé")


# DummyResponse pour simuler requests.post
class DummyResponse:
    def __init__(self, status_code=200, content=b'', text='', json_data=None):
        self.status_code = status_code
        self.content = content
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json

    @property
    def ok(self):
        return self.status_code == 200


@pytest.fixture(autouse=True)
def mock_services(monkeypatch):
    # gRPC stub
    monkeypatch.setattr(grpc, 'insecure_channel', lambda addr: None)
    monkeypatch.setattr(montantmax_pb2_grpc, 'MontantMaxServiceStub', FakeMontantStub)

    # requests.post fake
    def fake_post(url, data=None, json=None, headers=None, timeout=None):
        # GraphQL risk
        if url == MS_PROFILRISQUE_URL:
            amt = json['variables']['loanAmount']
            risk = 'acceptable' if amt < 20000 else 'elevé'
            return DummyResponse(json_data={'riskProfile': risk})

        # SubmitChequeRequest SOAP
        if url == MS_BANQUE_URL:
            # renvoyer un XML avec un request_id fixe
            xml = b"""<?xml version='1.0' encoding='UTF-8'?>
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:tns="ms.banque.async">
  <soap11env:Body>
    <tns:SubmitChequeRequestResponse>
      <tns:SubmitChequeRequestResult>fixed-uuid-1234</tns:SubmitChequeRequestResult>
    </tns:SubmitChequeRequestResponse>
  </soap11env:Body>
</soap11env:Envelope>"""
            return DummyResponse(content=xml, text=xml.decode())

        # Demande de financement REST
        if url == MS_FOURNISSEUR_URL:
            return DummyResponse(status_code=200, json_data={'status': 'success'})

        return DummyResponse(status_code=404)

    monkeypatch.setattr("requests.post", fake_post)


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c


def test_missing_data(client):
    rv = client.post('/loan')
    assert rv.status_code == 400
    js = rv.get_json()
    assert js['status'] == 'error'


def test_invalid_amount_type(client):
    rv = client.post('/loan', json={'id':'1','personal_info':'x','loan_amount':'abc'})
    assert rv.status_code == 400
    assert rv.get_json()['reason'].startswith("Le montant doit être un nombre")


def test_grpc_refuse(client):
    rv = client.post('/loan', json={'id':'1','personal_info':'x','loan_amount':60000})
    assert rv.status_code == 400
    assert rv.get_json()['status'] == 'refused'


def test_risk_refusal(client):
    rv = client.post('/loan', json={'id':'1','personal_info':'x','loan_amount':25000})
    assert rv.status_code == 400
    assert rv.get_json()['reason'] == 'Risque trop élevé'


def test_flow_async_success(client):
    # 1) soumission de la demande
    rv = client.post('/loan', json={'id':'1','personal_info':'x','loan_amount':10000})
    assert rv.status_code == 200
    js = rv.get_json()
    assert js['status'] == 'pending'
    req_id = js['request_id']

    # 2) avant callback, status pending
    rv2 = client.get(f'/loan/status/{req_id}')
    assert rv2.status_code == 200
    assert rv2.get_json()['status'] == 'pending'

    # 3) simulate callback valide
    soap = f"""<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <ChequeStatusResponse>
      <request_id>{req_id}</request_id>
      <status>done</status>
      <verdict>Chèque validé</verdict>
    </ChequeStatusResponse>
  </soapenv:Body>
</soapenv:Envelope>"""
    rv3 = client.post('/loan/callback', data=soap, content_type='text/xml')
    assert rv3.status_code == 200

    # 4) après callback, status approved
    rv4 = client.get(f'/loan/status/{req_id}')
    assert rv4.status_code == 200
    out = rv4.get_json()
    assert out['status'] == 'approved'
    assert 'fonds' in out['message']


def test_flow_async_invalid(client):
    # même soumission
    rv = client.post('/loan', json={'id':'1','personal_info':'x','loan_amount':10000})
    req_id = rv.get_json()['request_id']

    # callback invalide
    soap = f"""<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <ChequeStatusResponse>
      <request_id>{req_id}</request_id>
      <status>done</status>
      <verdict>Chèque invalide</verdict>
    </ChequeStatusResponse>
  </soapenv:Body>
</soapenv:Envelope>"""
    client.post('/loan/callback', data=soap, content_type='text/xml')

    # status refused
    rv2 = client.get(f'/loan/status/{req_id}')
    assert rv2.status_code == 400
    assert rv2.get_json()['status'] == 'refused'
