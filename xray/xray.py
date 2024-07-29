import os
import traceback
import boto3
import logging
from aws_xray_sdk.core import xray_recorder, patch_all, patch
from aws_xray_sdk.core.lambda_launcher import LambdaContext
from aws_xray_sdk.core import exceptions
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
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
        service='my-flask-app',
    )

   # XRayMiddleware(app, xray_recorder)
    #patch_all()

    s3_client = boto3.client('s3', region_name='us-east-1')
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    # Habilitar el seguimiento de X-Ray para los clientes

    patch(['boto3'])
    print("X-Ray initialization successful")
    return s3_client, ecs_client

#init_xray()

# Setup AWS session and clients with X-Ray integration
"""def setup_aws_clients():
    session = boto3.Session(profile_name='default')
    config = Config(region_name='us-east-1')

    ecr_client = session.client('ecr', config=config)
    ecs_client = session.client('ecs', config=config)

    xray_recorder.configure(service='ecr')
    xray_recorder.configure(service='ecs')

    return ecr_client, ecs_client"""

#ecr_client, ecs_client = setup_aws_clients()

# Setup environment from Parameter Store
def setup_environment():
    if aws_session:
        ssm_client = aws_session.client('ssm', region_name='us-east-1')

        parameter = ssm_client.get_parameter(
            Name='/prepod/utils_oas/xray/DaemonAddr',
            WithDecryption=True
        )

        daemon_addr = parameter['Parameter']['Value']
        os.environ['DAEMON_ADDR'] = daemon_addr
        return daemon_addr
    else:
        print("AWS session is not initialized")
        return None
        
"""def setup_environment():
    session = boto3.Session(profile_name='default')
    ssm_client = session.client('ssm', region_name='us-east-1')

    parameter = ssm_client.get_parameter(
        Name='/prepod/utils_oas/xray/DaemonAddr',
        WithDecryption=True
    )

    daemon_addr = parameter['Parameter']['Value']
    os.environ['DAEMON_ADDR'] = daemon_addr
    return daemon_addr"""

# Segments and subsegments
@app.before_request
def before_request():
    #segment = xray_recorder.begin_segment(name=request.host, traceid=request.headers.get('X-Amzn-Trace-Id'))
    #g.segment = segment
    """Inicia un segmento para la solicitud actual."""
    #segment_name = f"Flask: {request.path}"
    xray_recorder.begin_segment(name='Flask Request')

@app.after_request
def after_request(response):
    # Añadir metadatos HTTP al segmento
    segment = xray_recorder.current_segment()
    if segment:
        segment.put_http_meta('http.status', response.status_code)
    xray_recorder.end_segment()
    return response

def begin_subsegment(name, method, url, status):
    return xray_recorder.begin_subsegment(name)

def end_subsegment(subsegment, status, error=None):
    if error:
        subsegment.add_exception(error)
    subsegment.put_http_meta('response', {'status': status})
    xray_recorder.end_subsegment()

def update_state(status, error):
    segment = getattr(g, 'segment', None)
    if segment:
        segment.put_http_meta('response', {
            'status': status
        })
        if error:
            segment.add_exception(error)

@app.route('/')
def index():
    with xray_recorder.in_segment('index_segment') as segment:
        segment.put_metadata('method', request.method)
        segment.put_metadata('url', request.url)
    return 'Hello, X-Ray!', 200

@app.errorhandler(Exception)
def handle_500_error(e):
    # Manejo de excepciones y adición de metadatos al segmento
    segment = xray_recorder.current_segment()
    if segment:
        segment.add_exception(e, traceback.format_exc())
    return Response(
        f"An error occurred: {str(e)}",
        status=500,
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(debug=True)
