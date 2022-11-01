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


if __name__ == "__main__":
    nuxeo = init_nuxeo()
    #app = Flask("gestor_documental_mid")
    app.register_blueprint(api_bp)
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
    #pprint.pprint(json.dumps(api.__schema__)) #exporta la documentacion a formato json
    

