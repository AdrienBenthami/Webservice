# src/ms_banque/app.py
from spyne import Application, rpc, ServiceBase, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

class BanqueService(ServiceBase):
    @rpc(Unicode, _returns=Unicode)
    def ValidateCheck(ctx, check):
        # Simulation de validation du chèque
        if check == "valid":
            return "Chèque validé"
        else:
            return "Chèque invalide"

application = Application([BanqueService],
                          tns='ms.banque',
                          in_protocol=Soap11(validator='lxml'),
                          out_protocol=Soap11())

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    server = make_server('0.0.0.0', 5002, WsgiApplication(application))
    server.serve_forever()
