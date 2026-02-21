from nuxeo.client import Nuxeo
import os
import sys
import boto3

# Environmen variables list
variables = ['API_PORT', 'PARAMETER_STORE', 'NUXEO_URL', 'BUCKET_NAME', 'DOCUMENTOS_CRUD_URL']

api_cors_config = {
  "origins": ["*"],
  "methods": ["OPTIONS", "GET", "POST"],
  "allow_headers": ["Authorization", "Content-Type"]
}

def checkEnv():
  # Environment variables checking
  for variable in variables:
      if variable not in os.environ:
          print(str(variable) + " environment variable not found")
          sys.exit()

def get_param(name):
    ssm = boto3.client('ssm')
    return ssm.get_parameter(Name=name, WithDecryption=True)['Parameter']['Value']

def init_nuxeo():
    parameter_store = str(os.environ['PARAMETER_STORE'])
    nuxeo_username = get_param(f"/{parameter_store}/gestor_documental_mid/nuxeo/username")
    nuxeo_password = get_param(f"/{parameter_store}/gestor_documental_mid/nuxeo/password")

    return Nuxeo(
      host=str(os.environ['NUXEO_URL']),
      auth=(nuxeo_username, nuxeo_password)
    )