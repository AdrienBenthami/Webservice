# src/ms_montantmax/server.py
from concurrent import futures
import grpc
import montantmax_pb2
import montantmax_pb2_grpc

MAX_LOAN_AMOUNT = 50000  # Exemple de plafond autorisé

class MontantMaxService(montantmax_pb2_grpc.MontantMaxServiceServicer):
    def CheckLoan(self, request, context):
        if request.loan_amount <= MAX_LOAN_AMOUNT:
            return montantmax_pb2.LoanResponse(allowed=True, message="Montant autorisé")
        else:
            return montantmax_pb2.LoanResponse(allowed=False, message="Montant trop élevé")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    montantmax_pb2_grpc.add_MontantMaxServiceServicer_to_server(MontantMaxService(), server)
    server.add_insecure_port('[::]:50051')
    print("MS MontantMax est en cours d'exécution sur le port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
