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

xray_recorder_global = xray_recorder

# Configuración de X-Ray
def init_xray(app):
    os.environ['AWS_XRAY_NOOP_ID'] = 'true'
    os.environ['AWS_XRAY_DEBUG_MODE'] = 'TRUE'

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('aws_xray_sdk')

    set_xray_recorder()
    #patch_all()

    s3_client = boto3.client('s3', region_name='us-east-1')
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    # Habilitar el seguimiento de X-Ray para los clientes

    patch(['boto3'])
    print("X-Ray initialization successful")
    return s3_client, ecs_client

def before_request():
    """Crea un nuevo segmento principal para cada solicitud."""
    segment_name = request.host
    print("SI ENTRA ", segment_name)
    xray_recorder_global.begin_segment(name=segment_name)
    print(xray_recorder_global.current_segment())

def after_request(response: Response):
    """Finaliza el segmento principal después de cada solicitud."""
    print("SI SALE")
    segment = xray_recorder_global.current_segment()
    print("segment sale ", segment)
    if segment:
        print("Segment:", segment.id)
        segment.put_http_meta('method', request.method)
        segment.put_http_meta('url', request.url)
        segment.put_http_meta('status', response.status_code)
        xray_recorder_global.end_segment()
    else:
        print("No active segment found")
    return response

def setup_xray_filters(app):
    """Configura los filtros para X-Ray en la aplicación Flask."""
    app.before_request(before_request)
    app.after_request(after_request)

def get_xray_recorder():
    """Devuelve el xray_recorder configurado."""
    return xray_recorder_global

def set_xray_recorder():
    xray_recorder_global.configure(
        daemon_address='3.81.69.43:2000',
        sampling=True,
        context_missing='LOG_ERROR',
        service=app
    )
    return xray_recorder_global
