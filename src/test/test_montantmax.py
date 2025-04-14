# src/test/test_montantmax.py

import os
import sys

# Ajoute le répertoire parent (src) au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import grpc
from ms_montantmax import montantmax_pb2, montantmax_pb2_grpc

def test_montantmax(amount):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = montantmax_pb2_grpc.MontantMaxServiceStub(channel)
        request = montantmax_pb2.LoanRequest(loan_amount=amount)
        response = stub.CheckLoan(request)
        print(f"Montant demandé: {amount}, Autorisé: {response.allowed}, Message: {response.message}")

if __name__ == '__main__':
    # Test avec un montant dans la limite autorisée
    test_montantmax(30000)
    # Test avec un montant dépassant le plafond
    test_montantmax(60000)
