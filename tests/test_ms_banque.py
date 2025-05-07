import sys
import pytest
# module‐level skip si Python > 3.10
if sys.version_info >= (3, 11):
    pytest.skip("Les tests de ms_banque nécessitent Spyne <-= 3.10", allow_module_level=True)
    
    
from spyne.server.wsgi import WsgiApplication
from ms_banque.server import application, _STORE
from werkzeug.test import Client
from werkzeug.wrappers import Response
from lxml import etree


@pytest.fixture(autouse=True)
def flush_store():
    _STORE.clear()
    yield
    _STORE.clear()

@pytest.fixture
def client():
    wsgi_app = WsgiApplication(application)
    return Client(wsgi_app, Response)

def _parse_response(resp):
    return etree.fromstring(resp.data)

def test_submit_and_get_and_upload_and_get(client):
    # 1) SubmitChequeRequest
    submit_soap = b'''<?xml version="1.0"?>\
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\
<soapenv:Body><SubmitChequeRequest xmlns="ms.banque.async"/></soapenv:Body></soapenv:Envelope>'''
    resp1 = client.post('/', data=submit_soap, headers={'Content-Type':'application/soap+xml'})
    assert resp1.status_code == 200
    tree1 = _parse_response(resp1)
    ns = {'tns':'ms.banque.async'}
    req_id = tree1.findtext('.//tns:SubmitChequeRequestResult', namespaces=ns)
    assert req_id

    # 2) GetChequeStatus → pending
    get_soap = f'''<?xml version="1.0"?>\
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\
<soapenv:Body><GetChequeStatus xmlns="ms.banque.async">\
<request_id>{req_id}</request_id></GetChequeStatus>\
</soapenv:Body></soapenv:Envelope>'''.encode()
    resp2 = client.post('/', data=get_soap, headers={'Content-Type':'text/xml'})
    tree2 = _parse_response(resp2)
    assert tree2.findtext('.//tns:status', namespaces=ns) == 'pending'

    # 3) UploadCheque → valid
    upload_soap = f'''<?xml version="1.0"?>\
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\
<soapenv:Body><UploadCheque xmlns="ms.banque.async">\
<request_id>{req_id}</request_id><cheque>valid</cheque>\
</UploadCheque></soapenv:Body></soapenv:Envelope>'''.encode()
    resp3 = client.post('/', data=upload_soap, headers={'Content-Type':'text/xml'})
    assert resp3.status_code == 200

    # 4) GetChequeStatus → done + Chèque validé
    resp4 = client.post('/', data=get_soap, headers={'Content-Type':'text/xml'})
    tree4 = _parse_response(resp4)
    assert tree4.findtext('.//tns:status', namespaces=ns) == 'done'
    assert tree4.findtext('.//tns:verdict', namespaces=ns) == 'Chèque validé'
