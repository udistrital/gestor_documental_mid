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
        return Response("{'Status':'200'}", status=200, mimetype='application/json')
    except Exception as e:
        logging.error("type error: " + str(e))
        return Response(json.dumps({'Status':'500'}), status=500, mimetype='application/json')


##pprint.pprint(nuxeo.documents.get_children(path='/default-domain/workspaces/oas/oas_app/Cumplidos'))

app = Flask(__name__)
CORS(app)
api = Api(app)

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

@app.route("/upload", methods=["POST"])
@cross_origin(**api_cors_config)
def post_example():
    data = request.get_json()
    pprint.pprint(data)
    pprint.pprint(type(data))
    IdDocumento = data[0]['IdDocumento']
    res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'tipo_documento/'+str(IdDocumento)).content
    res_json = json.loads(res.decode('utf8').replace("'", '"'))
    
    pprint.pprint(res_json)
    pprint.pprint(type(res_json))


    up_file = Document(
    name = data[0]['nombre'],
    type = res_json['TipoDocumentoNuxeo'],
    properties={
        'dc:title': data[0]['nombre'],
    })

    pprint.pprint(up_file)
    pprint.pprint(type(up_file))

    file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))

    # Create a batch
    batch = nuxeo.uploads.batch()
    #blob = FileBlob(data[0]['file'])
    blob = base64.b64decode(data[0]['file'])
    pprint.pprint(blob)
    pprint.pprint(type(blob))

    with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
     fout.write(blob)

    try:
        uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
        # uploaded = batch.upload(BufferBlob(data[0]['file']), chunked=True)
        #uploaded = batch.upload(blob)
    except UploadError:
        return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')

    # Attach it to the file
    operation = nuxeo.operations.new('Blob.AttachOnDocument')
    operation.params = {'document': str(res_json['Workspace'])+'/'+data[0]['nombre']}
    operation.input_obj = uploaded
    operation.execute()

    return Response(json.dumps({'Status':'200'}), status=200, mimetype='application/json')


class document(Resource):
        
    def post(self, filename, file_object, properties):
        pprint.pprint(self)
        pprint.pprint(filename)
        pprint.pprint(file_object)
        pprint.pprint(properties)
    
    def get(self, uid):
        try:
            #logging.info("Start fetching")
            #logging.info(pformat(nuxeo.documents.get(uid=uid)))
            #pprint.pprint(type(nuxeo.documents.get(uid=uid).properties))
            #pprint.pprint(type(nuxeo.documents.get(uid=uid)))
            doc = nuxeo.documents.get(uid = uid)
            #DicRes = nuxeo.documents.get(uid=uid).properties
            DicRes = doc.properties
            blob_get = doc.fetch_blob()
            blob64 = base64.b64encode(blob_get)
            DicRes['file'] = str(blob64)
            # pprint.pprint(blob_get)
            # pprint.pprint(type(blob_get))
            return Response(json.dumps(DicRes), status=200, mimetype='application/json')
        except Exception as e:
            pprint.pprint("type error: " + str(e))
            return Response(json.dumps({'Status':'500','Error':'IDNotFound'}), status=500, mimetype='application/json')
            

class metadata(Resource):
        
    def post(self, uid):
        data = request.get_json()
        return set_metadata(uid, data['properties'])

api.add_resource(metadata, '/document/<string:uid>/metadata')
api.add_resource(document, '/document/<string:uid>')

if __name__ == "__main__":
    nuxeo = init_nuxeo()
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
