from nuxeo.client import Nuxeo
from nuxeo.models import Document, FileBlob, BufferBlob
from nuxeo.exceptions import UploadError
from flask import Flask, Response, request, Blueprint, abort
from flask_cors import CORS, cross_origin
#from flask_restful import Api, Resource
from flask_restx import Api, Resource, reqparse, fields, inputs
import os
import sys
import json, yaml
import pprint
import logging
import requests
import base64
#librerias de firma electronica 
from cryptography.exceptions import InvalidSignature
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import http_import
#from app.electronicSign import ElectronicSign

# Imports ElectronicSign
from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pdfminer.high_level import extract_pages
from textwrap import wrap
from datetime import datetime
import time
# __________________________

# Nuxeo client
nuxeo = None

# Environmen variables list
variables = ['API_PORT', 'NUXEO_URL', 'NUXEO_USERNAME', 'NUXEO_PASSWORD', 'DOCUMENTOS_CRUD_URL']

api_cors_config = {
  "origins": ["*"],
  "methods": ["OPTIONS", "GET", "POST"],
  "allow_headers": ["Authorization", "Content-Type"]
}

# Environment variables checking
for variable in variables:
    if variable not in os.environ:
        print(str(variable) + " environment variable not found")
        sys.exit()

def init_nuxeo():
    return Nuxeo(
        host=str(os.environ['NUXEO_URL']),
        auth=(str(os.environ['NUXEO_USERNAME']), str(os.environ['NUXEO_PASSWORD']))
    )


def set_metadata(uid, metadata):
    try:    
        doc = nuxeo.documents.get(uid = uid)
        for prop, value in metadata.items():
            doc.properties[prop] = value
        doc.save()
        return Response(json.dumps({'Status':'200'}), status=200, mimetype='application/json')
    except Exception as e:
        logging.error("type error: " + str(e))
        return Response(json.dumps({'Status':'500'}), status=500, mimetype='application/json')


##pprint.pprint(nuxeo.documents.get_children(path='/default-domain/workspaces/oas/oas_app/Cumplidos'))

app = Flask(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/v1")
CORS(api_bp)
#api = Api(app,version='1.0', title='gestor_documental_mid', description='Api mid para la autenticacion de documentos en Nuxeo', doc=False,) #produccion
api = Api(api_bp,version='1.0', title='gestor_documental_mid', description='Api mid para la autenticacion de documentos en Nuxeo', doc="/swagger")
nx = api.namespace("/", description="Nuxeo service Healthcheck")
dc = api.namespace("document", description="Nuxeo document operations")
request_parser = reqparse.RequestParser(bundle_errors=True)
request_parser.add_argument('list', location='json', type=list, required=True)
query_parser = reqparse.RequestParser()
query_parser.add_argument('versionar', type=bool, help='Conservar documento en Nuxeo?', default=False)

metadata_doc_crud_model = api.model('documentos_crud_metadata', {
    'dato_a': fields.String,
    'dato_b': fields.String,
    'dato_n': fields.String
})

nuxeo_tags = api.model('nuxeo_tags', {
    'label': fields.String,
    'username': fields.String
})

properties = api.model('Metadata_properties', {
    'dc:description': fields.String,
    'dc:source': fields.String,
    'dc:publisher': fields.String,
    'dc:rights': fields.String,
    'dc:title': fields.String,
    'dc:language': fields.String,
    'nxtag:tags': fields.Nested(nuxeo_tags,as_list=True)
})

metadata_dublin_core_model = api.model('Nuxeo_dublin_core_metadata', {
    'properties': fields.Nested(properties)
})

upload_model = [api.model('upload_resquest', {
    'IdTipoDocumento': fields.Integer,
    'nombre': fields.String,
    #'metadatos': fields.String(default='{}'),
    'metadatos': fields.Nested(metadata_doc_crud_model),
    'descripcion': fields.String,
    'file': fields.String,
})]

# Class ElectronicSign
class ElectronicSign:
    def __init__(self):
        self.YFOOTER = 80
        self.YHEEADER = 100

    def lastPageItems(self, pdfIn):
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        #pages = PDFPage.get_pages(pdfIn)
        pages = extract_pages(pdfIn)
        pages = list(pages)
        page = pages[len(pages)-1]

        yText = []

        for lobj in page:
            if isinstance(lobj, LTTextBox):
                x, y, text = lobj.bbox[0], lobj.bbox[3], lobj.get_text()
                yText.append(y)

        return yText

    def signPosition(self, pdfIn):
        yText = self.lastPageItems(pdfIn)
        yText.reverse()

        for i in range(1,19):
            if yText[i] > 80:
                y = yText[i]
                break

        return y-20
        
    def signature(self, pdfIn, yPosition, datos):
        x = 80
        y = yPosition
        signPageSize = 3 + len(datos["firmantes"]) + len(datos["representantes"]) + 2.5 #Espacios

        wraped_firmantes = []
        for firmante in datos["firmantes"]:
            text = firmante["cargo"] + ": " + firmante["nombre"] + ". " + firmante["tipoId"] + " " + firmante["identificacion"]
            text = "\n".join(wrap(text, 60))
            signPageSize += text.count("\n")
            wraped_firmantes.append(text)

        wraped_representantes = []
        for representante in datos["representantes"]:
            text = representante["cargo"] + ": " + representante["nombre"] + ". " + representante["tipoId"] + " " + representante["identificacion"]
            text = "\n".join(wrap(text, 60))
            text.count("\n")
            signPageSize += text.count("\n")
            wraped_representantes.append(text)

        wraped_firma = "\n".join(wrap(datos["firma"], 60))
        signPageSize += wraped_firma.count("\n")

        signPageSize *= 10

        if(yPosition - self.YFOOTER < signPageSize):
            y = PdfFileReader(pdfIn).getPage(0).mediabox[3] - self.YHEEADER 
        
        c = canvas.Canvas('documents/signature.pdf')
        # Create the signPdf from an image
        # c = canvas.Canvas('signPdf.pdf')

        # Draw the image at x, y. I positioned the x,y to be where i like here
        # c.drawImage('test.png', 15, 720)
        pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
        pdfmetrics.registerFont(TTFont('VeraBd', 'VeraBd.ttf'))

        c.setFont('VeraBd', 10)
        y = y - 10
        c.drawString(x + 20, y,"Firmado Digitalmente")
        
        c.setFont('Vera', 8)
        t = c.beginText()
        
        if len(datos["firmantes"]) > 1:
            t.setFont('VeraBd', 8)
            y = y - 15
            t.setTextOrigin(x, y)
            t.textLine("Firmantes:")
        elif len(datos["firmantes"]) == 1:
            t.setFont('VeraBd', 8)
            y = y - 15
            t.setTextOrigin(x, y)
            t.textLine("Firmante:")

        count = 1
        t.setFont('Vera', 8)
        for firmante in wraped_firmantes:
            if(count > 1):
                y = y - 10
            t.setTextOrigin(x+140,y)
            t.textLines(firmante)
            y = y-firmante.count("\n")*10
            count += 1

        if len(wraped_firmantes):
            y = y - 5

        if len(datos["representantes"]) > 1:
            t.setFont('VeraBd', 8)
            y = y - 10
            t.setTextOrigin(x, y)
            t.textLine("Representantes:")
        elif len(datos["representantes"]) == 1:
            t.setFont('VeraBd', 8)
            y = y - 10
            t.setTextOrigin(x, y)
            t.textLine("Representante:")

        count = 1
        t.setFont('Vera', 8)
        for representante in wraped_representantes:
            if(count > 1):
                y = y - 10
            t.setTextOrigin(x+140,y)
            t.textLines(representante)
            y = y-representante.count("\n")*10
            count += 1

        if len(wraped_representantes):
            y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10
        t.setTextOrigin(x, y)
        t.textLine("Tipo de documento:")
        t.setFont('Vera', 8)
        t.setTextOrigin(x+140, y)
        t.textLine(datos["tipo_documento"])

        y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10
        t.setTextOrigin(x, y)
        t.textLine("Firma elecronica:")
        t.setFont('Vera', 8)
        t.setTextOrigin(x+140, y)
        t.textLines(wraped_firma)

        y = y - 5

        t.setFont('VeraBd', 8)
        y = y - 10 - wraped_firma.count("\n")*10
        t.setTextOrigin(x, y)
        t.textLine("Fecha y hora:")
        t.setFont('Vera', 8)
        fechaHoraActual = time.strftime("%x") + " " + time.strftime("%X")
        t.setTextOrigin(x+140, y)
        t.textLine(fechaHoraActual)

        c.drawText(t)
        c.showPage()
        c.save()

        if(yPosition - self.YFOOTER > signPageSize):
            return True
        else:
            return False
        # c.drawString(x, y-45, "Tipo de documento: Certificado Laboral")
        # c.drawString(x, y-55, "Dirrección IP: 80.80.80.80")
        # c.drawString(x, y-35, "Fecha y hora: 16/11/2022 07:15 UTC")
        # c.drawString(x, y-25, "Firma Electronica: " + firma_electronica["llaves"]["firma"])

        # c.drawString(x+250, y-25, "Firma Electronica: x12a-2313-o0in-31af")
        # c.drawString(x+250, y-35, "Fecha y hora: 16/11/2022 07:15 UTC")
        # c.drawString(x+250, y-45, "Tipo de documento: Certificado Laboral")
        # c.drawString(x+250, y-55, "Dirrección IP: 80.80.80.80")
            
        # c.save() 

    def estamparUltimaPagina(self, pdfIn):
        signPdf = PdfFileReader(open("signature.pdf", "rb"))
        documentPdf = PdfFileReader(pdfIn)
        
        # Get our files ready
        output_file = PdfFileWriter()

        # Number of pages in input document
        page_count = documentPdf.getNumPages()

        for page_number in range(page_count-1):
            input_page = documentPdf.getPage(page_number)
            output_file.addPage(input_page)

        input_page = documentPdf.getPage(page_count-1)
        input_page.mergePage(signPdf.getPage(0))
        output_file.addPage(input_page)

        with open("documents/documentSigned.pdf", "wb") as outputStream:
            output_file.write(outputStream)

    def estamparNuevaPagina(self, pdfIn):
        signPdf = PdfFileReader(open("documents/signature.pdf", "rb"))
        documentPdf = PdfFileReader(pdfIn)

        # Get our files ready
        output_file = PdfFileWriter()

        # Number of pages in input document
        page_count = documentPdf.getNumPages()

        for page_number in range(page_count):
            input_page = documentPdf.getPage(page_number)
            output_file.addPage(input_page)

        
        output_file.addBlankPage()
        output_file.getPage(output_file.getNumPages()-1).mergePage(signPdf.getPage(0))

        with open("documents/documentSigned.pdf", "wb") as outputStream:
            output_file.write(outputStream)


    def estamparFirmaElectronica(self, datos):
        pdfIn = open("documents/documentToSign.pdf","rb")
        yPosition = self.signPosition(pdfIn)
        suficienteEspacio = self.signature(pdfIn, yPosition, datos)

        if suficienteEspacio:
            self.estamparUltimaPagina(pdfIn)
        else:
            self.estamparNuevaPagina(pdfIn)

    #_________________________________________


#@api.route('/')
@nx.route("/")
class Healthcheck(Resource):
    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error'
    })            
    #@app.route('/', methods=['GET'])
    @cross_origin(**api_cors_config)
    def get(self):
        try:
            if nuxeo.client.is_reachable():
                data = json.loads(json.dumps(api.__schema__))            
                with open('swagger.json', 'w') as jsonf:
                    jsonf.write(json.dumps(api.__schema__))

                with open('swagger.yml', 'w') as yamlf:
                    yaml.dump(data, yamlf, allow_unicode=True, default_flow_style=False)

                DicStatus = {
                    'Status':'ok',
                    'Code':'200'
                }
                
                return Response(json.dumps(DicStatus),status=200,mimetype='application/json')
            else:
                logging.error("Nuxeo service fail")
                DicStatus = {
                    'Status':'Nuxeo service fail',
                    'Code':'500'
                }
                return Response(json.dumps(DicStatus), status=500, mimetype='application/json')
        except Exception as e:
            logging.error("type error: " + str(e))
            return Response(json.dumps({'Status':'500'}), status=500, mimetype='application/json')

def firmar(plain_text):
    try:
        #objeto_firmado = []
        # genera un par de claves 
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        #serializacion de llaves 
        pem_privada = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        pem_publica = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        # firma el documento
        signature = private_key.sign(
            data=plain_text.encode('utf-8'),
            padding=padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            algorithm=hashes.SHA256()
        )

        mascara = abs(hash(str(pem_publica)))
        objeto_firmado = {
            "codigo_autenticidad": str(mascara),
            "llaves": {
                "llave_publica": base64.urlsafe_b64encode(pem_publica).decode("utf-8"),
                "llave_privada": base64.urlsafe_b64encode(pem_privada).decode("utf-8"),
                "firma": base64.urlsafe_b64encode(signature).decode("utf-8")
            }
        }
        #string_json = str(objeto_firmado).replace("{'", '{ \ "').replace("': '", ' \ ": \ "').replace("': ", ' \ ": ').replace(", '", ', \ "').replace("',", '",').replace('",' , ' \ ",').replace("'}", ' \ " } ').replace(" ", "").replace('\\"', '\"')
        return objeto_firmado
        #return string_json
    except UnsupportedAlgorithm:        
        logging.error("signature failed, type error: " + str(UnsupportedAlgorithm))


#@api.route('/upload')
@dc.route("/upload")
class Upload(Resource):
    #@app.route("/upload", methods=["POST"])
    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=upload_model)
    @dc.expect(request_parser)
    @cross_origin(**api_cors_config)
    def post(self):
        response_array = []
        try:            
            data = request.get_json()
            for i in range(len(data)):
                if len(str(data[i]['file'])) < 1000:
                    error_dict = {
                        'Status':'invalid pdf file',
                        'Code':'400'
                    }                
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            

                IdDocumento = data[i]['IdTipoDocumento']
                res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento))

                if res.status_code == 200:                
                    res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                    up_file = Document(
                    name = data[i]['nombre'],
                    type = res_json['TipoDocumentoNuxeo'],
                    properties={
                        'dc:title': data[i]['nombre'],
                    })
                    file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
                    # Create a batch
                    batch = nuxeo.uploads.batch()
                    blob = base64.b64decode(data[i]['file'])
                    with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
                        fout.write(blob)
                    try:
                        uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
                        #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                    except UploadError:
                        return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                    # Attach it to the file
                    operation = nuxeo.operations.new('Blob.AttachOnDocument')
                    #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
                    operation.params = {'document': str(file.uid)}
                    operation.input_obj = uploaded
                    operation.execute()        
                    firma_electronica = firmar(str(data[i]['file']))
                    all_metadata = str({** firma_electronica, ** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')
                    DicPostDoc = {
                        'Enlace' : str(file.uid),
                        'Metadatos' : all_metadata,
                        'Nombre' : data[i]['nombre'],
                        "Descripcion": data[i]['descripcion'],
                        'TipoDocumento' :  res_json,
                        'Activo': True
                    }
                    resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content
                    dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                    response_array.append(dictFromPost)
                else:
                    return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
            dictFromPost = response_array if len(response_array) > 1 else dictFromPost
            return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
        except Exception as e:            
                logging.error("type error: " + str(e))

                if str(e) == "'IdTipoDocumento'":
                    error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif str(e) == "'nombre'":
                    error_dict = {'Status':'the field nombre is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')
                elif str(e) == "'file'":
                    error_dict = {'Status':'the field file is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
                elif str(e) == "'metadatos'":                
                    error_dict = {'Status':'the field metadatos is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif '400' in str(e):
                    DicStatus = {'Status':'invalid request body', 'Code':'400'}
                    return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
                return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')


@dc.route("/store_document")
class Store_Document(Resource):
    @api.doc(responses={
        200: "Success",
        500: "Nuxeo error",
        400: "Bad request"
    }, body = upload_model)
    @dc.expect(request_parser)
    @cross_origin(**api_cors_config)
    def post(self):
        response_array = []
        try:
            data = request.get_json()
            #Se hace un ciclo para iterar sobre el array que se recibe en formato json, se recibe uno normalmente
            for i in range(len(data)):
                #Se valida que sea un archivo en pdf
                if len(str(data[i]['file'])) < 1000:
                    error_dict = {
                        'Status': 'Invalid pdf file',
                        'Code': '400'
                    }
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')

                idTipoDocumento = data[i]['IdTipoDocumento']
                res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(idTipoDocumento))

                if res.status_code == 200:
                    res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                    up_file_to_nuxeo = Document(
                        name = data[i]['nombre'],
                        type = res_json['TipoDocumentoNuxeo'],
                        properties = {
                            'dc:title': data[i]['nombre'],
                        }
                    )

                    file = nuxeo.documents.create(up_file_to_nuxeo, parent_path=str(res_json['Workspace']))

                    batch = nuxeo.uploads.batch()
                    blob = base64.b64decode(data[i]['file'])
                    with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
                        fout.write(blob)
                    try:
                        uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
                        #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                    except UploadError:
                        return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                    # Attach it to the file
                    operation = nuxeo.operations.new('Blob.AttachOnDocument')
                    #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
                    operation.params = {'document': str(file.uid)}
                    operation.input_obj = uploaded
                    operation.execute()

                    metadata = str({** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')

                    metadatos_to_documentos = {
                        'Enlace':       str(file.uid),
                        'Metadatos':    metadata,
                        'Nombre':       data[i]['nombre'],
                        "Descripcion":  data[i]['descripcion'],
                        'TipoDocumento':res_json,
                        'Activo':       True
                    }
                    
                    resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=metadatos_to_documentos).content
                    dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                    response_array.append(dictFromPost)

                else:
                    return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
            
            dictFromPost = response_array if len(response_array) > 1 else dictFromPost
            return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
        
        except Exception as exception:
                logging.error("type error: " + str(exception))
                if str(exception) == "'IdTipoDocumento'":
                    error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif str(exception) == "'nombre'":
                    error_dict = {'Status':'the field nombre is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')
                elif str(exception) == "'file'":
                    error_dict = {'Status':'the field file is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
                elif str(exception) == "'metadatos'":                
                    error_dict = {'Status':'the field metadatos is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif '400' in str(exception):
                    DicStatus = {'Status':'invalid request body', 'Code':'400'}
                    return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
                return Response(json.dumps({'Status':'500','Error':str(exception)}), status=500, mimetype='application/json')


#@api.route('/firma_electronica')
@dc.route("/firma_electronica")
class Firma_Electronica(Resource):
    #@app.route("/firma_electronica", methods=["POST"])
    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=upload_model)
    @dc.expect(request_parser)
    @cross_origin(**api_cors_config)
    def post(self):
        response_array = []
        try:            
            data = request.get_json()
            for i in range(len(data)):
                if len(str(data[i]['file'])) < 1000:
                    error_dict = {
                        'Status':'invalid pdf file',
                        'Code':'400'
                    }                
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            

                IdDocumento = data[i]['IdTipoDocumento']
                res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento))

                if res.status_code == 200:                
                    res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                    up_file = Document(
                    name = data[i]['nombre'],
                    type = res_json['TipoDocumentoNuxeo'],
                    properties={
                        'dc:title': data[i]['nombre'],
                    })
                    file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
                    # Create a batch
                    batch = nuxeo.uploads.batch()
                    blob = base64.b64decode(data[i]['file'])
                    with open(os.path.expanduser('./documents/documentToSign.pdf'), 'wb') as fout:
                        fout.write(blob)
                      
                    firma_electronica = firmar(str(data[i]['file']))

                    datos = {
                        "firma": firma_electronica["llaves"]["firma"],
                        "firmantes": data[i]["firmantes"],
                        "representantes": data[i]["representantes"],
                        "tipo_documento": res_json["Nombre"]
                    }


                    electronicSign = ElectronicSign()
                    electronicSign.estamparFirmaElectronica(datos)

                    all_metadata = str({** firma_electronica, ** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')

                    DicPostDoc = {
                        'Metadatos': all_metadata,
                        "firmantes": data[i]["firmantes"], 
                        "representantes": data[i]["representantes"], 
                        'Nombre': data[i]['nombre'],
                        "Descripcion": data[i]['descripcion'],
                        'TipoDocumento' :  res_json,
                        'Activo': True
                    }

                    try:
                        uploaded = batch.upload(FileBlob('./documents/documentSigned.pdf'), chunked=True)
                        #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                    except UploadError:
                        return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                    # Attach it to the file
                    operation = nuxeo.operations.new('Blob.AttachOnDocument')
                    #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
                    operation.params = {'document': str(file.uid)}
                    operation.input_obj = uploaded
                    operation.execute()      

                    resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content
                    dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                    response_array.append(dictFromPost)
                else:
                    return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
            dictFromPost = response_array if len(response_array) > 1 else dictFromPost
            return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
        except Exception as e:            
                logging.error("type error: " + str(e))

                if str(e) == "'IdTipoDocumento'":
                    error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif str(e) == "'nombre'":
                    error_dict = {'Status':'the field nombre is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')
                elif str(e) == "'file'":
                    error_dict = {'Status':'the field file is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
                elif str(e) == "'metadatos'":                
                    error_dict = {'Status':'the field metadatos is required','Code':'400'}
                    return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
                elif '400' in str(e):
                    DicStatus = {'Status':'invalid request body', 'Code':'400'}
                    return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
                return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')


#@api.route('/document/<string:uid>', doc={'params':{'uid': 'UID del documento generado en Nuxeo'}})#@api.doc(params={'uid': 'UID del documento generado en Nuxeo'})
@dc.route('/<string:uid>', doc={'params':{'uid': 'UID del documento generado en Nuxeo'}})
class document(Resource):        

    @app.errorhandler(404)
    def not_found_resource(e):
        DicStatus = {
            'Status':'Not found resource',
            'Code':'404'
        }
        return Response(json.dumps(DicStatus), status=404, mimetype='application/json')        

    @app.errorhandler(400)
    def invalid_parameter(e):
        DicStatus = {
            'Status':'invalid parameter',
            'Code':'400'
        }
        return Response(json.dumps(DicStatus), status=400, mimetype='application/json')        
    

    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    })    
    @cross_origin(**api_cors_config)
    def get(self, uid):        
        try:                  
            resource = uid
            if resource is None:
                abort(404, description="Not found resource")

            if uid.count('-') != 4 or len(uid) != 36:                
                abort(400, description="invalid parameter")

            res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)
            res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
            if str(res_json) != "[{}]":                 
                doc = nuxeo.documents.get(uid = uid)
                DicRes = doc.properties
                blob_get = doc.fetch_blob()
                blob64 = base64.b64encode(blob_get)
                DicRes['file'] = str(blob64).replace("b'","'").replace("'","")       
                return Response(json.dumps(DicRes), status=200, mimetype='application/json')
            else:
                DicStatus = {
                    'Status':'document not found',
                    'Code':'404'
                }
                return Response(json.dumps(DicStatus), status=404, mimetype='application/json')
        except Exception as e:
            logging.error("type error: " + str(e))
            if '400' in str(e):
                DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    })
    @dc.expect(query_parser)
    @cross_origin(**api_cors_config)
    def delete(self, uid):        
        try:                        
            versionar = request.args.get("versionar")
            versionar = False if versionar is None else eval(versionar.capitalize())

            if uid.count('-') != 4 or len(uid) != 36:                
                abort(400, description="invalid parameter")

            res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)    
            res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
            if str(res_json) != "[{}]":
                objeto = {
                    'Id': res_json[0]['Id'],
                    'Nombre': res_json[0]['Nombre'],
                    'Descripcion': res_json[0]['Descripcion'],
                    'Enlace': res_json[0]['Enlace'],
                    'TipoDocumento': res_json[0]['TipoDocumento'],
                    'Metadatos': res_json[0]['Metadatos'],
                    'Activo': False
                }
                res_del =  requests.put(str(os.environ['DOCUMENTOS_CRUD_URL']+'/documento/'+str(res_json[0]['Id'])), json=objeto )
                res_del_json = json.loads(res_del.content.decode('utf8').replace("'", '"'))
                DicStatus = {
                    'doc_deleted': res_del_json['Id'],
                    'nuxeo_doc_deleted': uid,
                    'Status':'ok',
                    'Code':'200'
                }
                if not versionar:
                    doc = nuxeo.documents.get(uid = uid)
                    doc.delete()
                return Response(json.dumps(DicStatus), status=200, mimetype='application/json')
            else:
                DicStatus = {
                    'Status':'document not found',
                    'Code':'404'
                }
                return Response(json.dumps(DicStatus), status=404, mimetype='application/json')
        except Exception as e:
            logging.error("type error: " + str(e))
            if '400' in str(e):
                DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')            
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')            

#-----------------------------------------------------funcion de eliminacion que si elimina-------------------------------------------------------
    #def delete(self, uid):        
        #try:                        
            #doc = nuxeo.documents.get(uid = uid)
            #doc.delete()
            #res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Enlace:'+uid)    
            #res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
            #res_del =  requests.delete(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento/'+str(res_json[0]['Id']))
            #res_del_json = json.loads(res_del.content.decode('utf8').replace("'", '"'))
            #DicStatus = {
                #'doc_deleted': res_del_json['Id'],
                #'nuxeo_doc_deleted': uid,
                #'Status':'ok',
                #'Code':'200'
            #}
            #return Response(json.dumps(DicStatus), status=200, mimetype='application/json')
        #except Exception as e:
            #logging.error("type error: " + str(e))
            #return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')            
#-----------------------------------------------------funcion de eliminacion que si elimina-------------------------------------------------------
@dc.route('/<string:uid>/metadata', doc={'params':{'uid': 'UID del documento generado en Nuxeo'}})
class Metadata(Resource):
    @api.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    },body=metadata_dublin_core_model)
    @dc.expect(request_parser)
    @cross_origin(**api_cors_config)
    def post(self, uid):#agrega metadatos al documento, en caso de agregar un metadato que no exista en el esquema este no lo tendra en cuenta             

        try:    
            if uid.count('-') != 4 or len(uid) != 36:                
                abort(400, description="invalid parameter")
            data = request.get_json()            
            if data is None or str(data) == "{}" :
                DicStatus = {'Status':'invalid request body','Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')        

            res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)    
            res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
            if str(res_json) != "[{}]":                
                return set_metadata(uid, data['properties']) 
            else:
                DicStatus = {'Status':'document not found', 'Code':'404'}
                return Response(json.dumps(DicStatus), status=404, mimetype='application/json')            
        except Exception as e:            
            logging.error("type error: " + str(e))
            if 'invalid parameter' in str(e):
                DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            if '400' in str(e):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')
            

#api.add_resource(Healthcheck, '/')
#api.add_resource(Metadata, '/document/<string:uid>/metadata')
#api.add_resource(document, '/document/<string:uid>')
#api.add_resource(Upload, '/upload')
#api.add_resource(Store_Document,'/store_document')


if __name__ == "__main__":
    nuxeo = init_nuxeo()
    #app = Flask("gestor_documental_mid")
    app.register_blueprint(api_bp)
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
    #pprint.pprint(json.dumps(api.__schema__)) #exporta la documentacion a formato json
    

