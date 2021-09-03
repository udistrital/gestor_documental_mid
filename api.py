from nuxeo.client import Nuxeo
from nuxeo.models import Document, FileBlob, BufferBlob
from nuxeo.exceptions import UploadError
from flask import Flask, Response, request
from flask_cors import CORS, cross_origin
from flask_restful import Api, Resource
import os
import sys
import json
from pprint import pformat
import pprint
import logging
import requests
import base64

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

def validate_document(nombre):    
    res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Nombre:'+nombre)    
    if res.status_code == 200:
        res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
        return True if str(res_json) != "[{}]" else False
    else:
        return res.status_code

##pprint.pprint(nuxeo.documents.get_children(path='/default-domain/workspaces/oas/oas_app/Cumplidos'))

app = Flask(__name__)
CORS(app)
api = Api(app)

class Root(Resource):
    @app.route('/', methods=['GET'])
    @cross_origin(**api_cors_config)
    def healthcheck():
        try:
            pprint.pprint(nuxeo.client.is_reachable())
            DicStatus = {
                'Status':'ok',
                'Code':'200'
            }
            return Response(json.dumps(DicStatus),status=200,mimetype='application/json')
        except Exception as e:
            logging.error("type error: " + str(e))
            return Response(json.dumps({'Status':'500'}), status=500, mimetype='application/json')

class Upload(Resource):
    @app.route("/upload", methods=["POST"])
    @cross_origin(**api_cors_config)
    def post():
        try:            
            data = request.get_json()#representa el cuerpo del json enviado por la peticion
            if not validate_document(data[0]['nombre']):
                IdDocumento = data[0]['IdDocumento']
                res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento)).content
                res_json = json.loads(res.decode('utf8').replace("'", '"'))
                up_file = Document(
                name = data[0]['nombre'],
                type = res_json['TipoDocumentoNuxeo'],
                properties={
                    'dc:title': data[0]['nombre'],
                })
                file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
                # Create a batch
                batch = nuxeo.uploads.batch()
                blob = base64.b64decode(data[0]['file'])
                with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
                    fout.write(blob)
                try:
                    uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
                    #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                except UploadError:
                    return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                # Attach it to the file
                operation = nuxeo.operations.new('Blob.AttachOnDocument')
                #operation.params = {'document': str(res_json['Workspace'])+'/'+data[0]['nombre']}
                operation.params = {'document': str(file.uid)}
                operation.input_obj = uploaded
                operation.execute()                
                DicPostDoc = {
                    'Enlace' : str(file.uid),
                    'Nombre' : data[0]['nombre'],
                    'TipoDocumento' :  res_json
                }                
                resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content            
                dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))
                return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
            elif validate_document(data[0]['nombre']) == True:
                return Response(json.dumps({'Status':'500','Error': str("the name "+data[0]['nombre']+" already exists in Nuxeo" )}), status=500, mimetype='application/json')
            else: 
                return Response(json.dumps({'Status':'500','Error': str("an error occurred in documentos_crud" )}), status=500, mimetype='application/json')        

        except Exception as e:            
                pprint.pprint("type error: " + str(e))
                return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

class document(Resource):
        
    def post(self, filename, file_object, properties):
        pprint.pprint(self)
        pprint.pprint(filename)
        pprint.pprint(file_object)
        pprint.pprint(properties)
    
    @cross_origin(**api_cors_config)
    def get(self, uid):
        
        try:                        
            #quemado = "prueba_core_2021_4"
            #pprint.pprint(validate_document(quemado))
            #if not validate_document(quemado):
            doc = nuxeo.documents.get(uid = uid)
            #DicRes = nuxeo.documents.get(uid=uid).properties            
            DicRes = doc.properties
            blob_get = doc.fetch_blob()
            blob64 = base64.b64encode(blob_get)
            DicRes['file'] = str(blob64)                        
            return Response(json.dumps(DicRes), status=200, mimetype='application/json')
            #else:
                #return Response(json.dumps({'Status':'500','Error': str("the name "+quemado+" already exists in Nuxeo" )}), status=500, mimetype='application/json')
        except Exception as e:
            pprint.pprint("type error: " + str(e))
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')
            

class Metadata(Resource):

    @cross_origin(**api_cors_config)
    def post(self, uid):#agrega metadatos al documento, en caso de agregar un metadato que no exista en el esquema este no lo tendra en cuenta 
        data = request.get_json()
        return set_metadata(uid, data['properties'])

api.add_resource(Root, '/')
api.add_resource(Metadata, '/document/<string:uid>/metadata')
api.add_resource(document, '/document/<string:uid>')
api.add_resource(Upload, '/upload')

if __name__ == "__main__":
    nuxeo = init_nuxeo()
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
