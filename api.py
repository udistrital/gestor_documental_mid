from nuxeo.client import Nuxeo
from flask import Flask, request
from flask_restful import Api, Resource, reqparse
import os
import sys

variables = ['API_PORT', 'NUXEO_URL', 'NUXEO_USERNAME', 'NUXEO_PASSWORD']

for variable in variables:
    if variable not in os.environ:
        print(str(variable) + " environment variable not found")
        sys.exit()

#nuxeo_password  = str(os.environ['NUXEO_PASSWORD'])
nuxeo = Nuxeo(
    host=str(os.environ['NUXEO_URL']),
    auth=(str(os.environ['NUXEO_USERNAME']), str(os.environ['NUXEO_PASSWORD']))
)

app = Flask(__name__)
api = Api(app)

class document(Resource):
        
    def post(self, filename, file_object, properties):
        pass
    
    def get(self):
        print("Holi")

api.add_resource(document, '/document')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))
