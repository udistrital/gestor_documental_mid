from nuxeo.client import Nuxeo
import os
import sys

# Environmen variables list
variables = ['API_PORT', 'NUXEO_URL', 'NUXEO_USERNAME', 'NUXEO_PASSWORD', 'DOCUMENTOS_CRUD_URL', 'ENCRYPTION_KEY']

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

def init_nuxeo():
    return Nuxeo(
        host=str(os.environ['NUXEO_URL']),
        auth=(str(os.environ['NUXEO_USERNAME']), str(os.environ['NUXEO_PASSWORD']))
    )