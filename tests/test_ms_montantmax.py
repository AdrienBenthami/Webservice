import pytest
from ms_montantmax.server import MontantMaxService
from ms_montantmax import montantmax_pb2

@pytest.fixture
def service():
    return MontantMaxService()

def test_checkloan_within_limit(service):
    req = montantmax_pb2.LoanRequest(loan_amount=1000)
    resp = service.CheckLoan(req, None)
    assert resp.allowed is True
    assert "Demande acceptée" in resp.message

def test_checkloan_above_limit(service):
    req = montantmax_pb2.LoanRequest(loan_amount=60000)
    resp = service.CheckLoan(req, None)
    assert resp.allowed is False
    assert "Montant trop élevé" in resp.message
