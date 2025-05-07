from spyne import Application, rpc, ServiceBase, Unicode, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from lxml import etree
import uuid, threading, requests

# --- store in-memory instead of Redis ---
_STORE = {}

class ChequeStatus(ComplexModel):
    status  = Unicode
    verdict = Unicode

def send_callback(request_id, reply_to, relates_to, verdict):
    NS_WSA = 'http://www.w3.org/2005/08/addressing'
    root = etree.Element(
        "{http://schemas.xmlsoap.org/soap/envelope/}Envelope",
        nsmap={None:"http://schemas.xmlsoap.org/soap/envelope/", 'wsa':NS_WSA}
    )
    hdr = etree.SubElement(root, "{http://schemas.xmlsoap.org/soap/envelope/}Header")
    etree.SubElement(hdr, f"{{{NS_WSA}}}MessageID").text   = str(uuid.uuid4())
    etree.SubElement(hdr, f"{{{NS_WSA}}}RelatesTo").text   = relates_to
    etree.SubElement(hdr, f"{{{NS_WSA}}}To").text         = reply_to

    body = etree.SubElement(root, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    resp = etree.SubElement(body, "ChequeStatusResponse")
    etree.SubElement(resp, "request_id").text = request_id
    etree.SubElement(resp, "status").text     = "done"
    etree.SubElement(resp, "verdict").text    = verdict

    xml = etree.tostring(root, xml_declaration=True, encoding='utf-8')
    try:
        requests.post(
            reply_to,
            data=xml,
            headers={'Content-Type':'application/soap+xml; charset=utf-8'},
            timeout=5
        )
    except:
        pass

class BanqueAsync(ServiceBase):
    __namespace__ = 'ms.banque.async'

    @rpc(_returns=Unicode)
    def SubmitChequeRequest(ctx):
        tree       = ctx.in_document
        ns_wsa     = {'wsa':'http://www.w3.org/2005/08/addressing'}
        reply_to   = tree.findtext('.//wsa:ReplyTo/wsa:Address', namespaces=ns_wsa) or ''
        relates_to = tree.findtext('.//wsa:MessageID',      namespaces=ns_wsa) or ''

        req_id = str(uuid.uuid4())
        _STORE[req_id] = {
            'status':     'pending',
            'verdict':    '',
            'reply_to':   reply_to,
            'relates_to': relates_to
        }
        return req_id

    @rpc(Unicode, Unicode, _returns=None)
    def UploadCheque(ctx, request_id, cheque):
        data = _STORE.get(request_id)
        if not data:
            return None
        verdict = "Chèque validé" if cheque == 'valid' else "Chèque invalide"
        data['status']  = 'done'
        data['verdict'] = verdict
        # lancer le callback en arrière-plan
        threading.Thread(
            target=send_callback,
            args=(request_id, data['reply_to'], data['relates_to'], verdict),
            daemon=True
        ).start()
        return None

    @rpc(Unicode, _returns=ChequeStatus)
    def GetChequeStatus(ctx, request_id):
        data = _STORE.get(request_id)
        if not data:
            return ChequeStatus(status='unknown', verdict='')
        return ChequeStatus(status=data['status'], verdict=data['verdict'])

application = Application(
    [BanqueAsync],
    tns='ms.banque.async',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('0.0.0.0', 5002, WsgiApplication(application))
    srv.serve_forever()
