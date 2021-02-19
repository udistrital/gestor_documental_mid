from nuxeo.client import Nuxeo
from flask import Flask, Response, request
from flask_restful import Api, Resource
import os
import sys
import json
from pprint import pformat
import pprint
import logging

# Nuxeo client
nuxeo = None

# Environmen variables list
variables = ['API_PORT', 'NUXEO_URL', 'NUXEO_USERNAME', 'NUXEO_PASSWORD']

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
        return Response("{'Status':'500'}", status=500, mimetype='application/json')


##pprint.pprint(nuxeo.documents.get_children(path='/default-domain/workspaces/oas/oas_app/Cumplidos'))

app = Flask(__name__)
api = Api(app)

@app.route('/', methods=['GET'])
def healthcheck():
    pprint.pprint(nuxeo.client.is_reachable())
    DicStatus = {
        'Status':'ok',
        'Code':'200'
    }

    return Response(json.dumps(DicStatus),status=200,mimetype='application/json')



class document(Resource):
        
    def post(self, filename, file_object, properties):
        pass
    
    def get(self, uid):
        logging.info("Start fetching")
        logging.info(pformat(nuxeo.documents.get(uid=uid)))
        #pprint.pprint(nuxeo.documents.get(uid=uid))
        logging.info("Finish fetching ")

class metadata(Resource):
        
    def post(self, uid):
        data = request.get_json()
        return set_metadata(uid, data['properties'])

api.add_resource(metadata, '/document/<string:uid>/metadata')
api.add_resource(document, '/document/<string:uid>')

if __name__ == "__main__":
    nuxeo = init_nuxeo()
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
