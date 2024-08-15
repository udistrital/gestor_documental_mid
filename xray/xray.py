import os
import boto3
import logging
from aws_xray_sdk.core import xray_recorder, patch_all, patch
from aws_xray_sdk.core.lambda_launcher import LambdaContext
from aws_xray_sdk.core import exceptions
from flask import Flask, Response, request, g
from botocore.config import Config

# Inicializa la aplicación Flask
app = Flask(__name__)

# Configuración de X-Ray
def init_xray(app):
    os.environ['AWS_XRAY_NOOP_ID'] = 'true'
    os.environ['AWS_XRAY_DEBUG_MODE'] = 'TRUE'

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('aws_xray_sdk')
    xray_recorder.configure(
        daemon_address='3.81.69.43:2000',
        sampling=True,
        context_missing='LOG_ERROR',
        #service='my-flask-app',
        service=app
    )

    patch_all()

    s3_client = boto3.client('s3', region_name='us-east-1')
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    # Habilitar el seguimiento de X-Ray para los clientes

    patch(['boto3'])
    print("X-Ray initialization successful")
    return s3_client, ecs_client
