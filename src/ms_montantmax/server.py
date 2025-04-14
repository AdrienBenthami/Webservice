# src/ms_montantmax/server.py
from concurrent import futures
import grpc
from ms_montantmax import montantmax_pb2
from ms_montantmax import montantmax_pb2_grpc

# Définir la classe de service en étendant la classe générée par gRPC
class MontantMaxService(montantmax_pb2_grpc.MontantMaxServiceServicer):
    def CheckLoan(self, request, context):
        # Par exemple, définissons un plafond autorisé
        plafond = 50000
        if request.loan_amount <= plafond:
            return montantmax_pb2.LoanResponse(
                allowed=True,
                message="Demande acceptée"
            )
        else:
            return montantmax_pb2.LoanResponse(
                allowed=False,
                message="Montant trop élevé"
            )

def serve():
    # Créer un serveur gRPC avec un pool de threads
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Ajouter notre service au serveur
    montantmax_pb2_grpc.add_MontantMaxServiceServicer_to_server(MontantMaxService(), server)
    # Écouter sur le port 5001
    server.add_insecure_port('[::]:50051')
    server.start()
    print("MS MontantMax gRPC server is running on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
