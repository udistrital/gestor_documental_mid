import traceback
import requests
import json
import io
import logging
from aws_xray_sdk.core import xray_recorder
from flask import request

# Importa la configuración de X-Ray
import xray

# Configuración del logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

global_header = ""

def set_header(header):
    global global_header
    global_header = header

def get_header():
    return global_header

def get_json(url, target):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    curr_url = request.host
    segment = xray_recorder.begin_segment(name=curr_url)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    except Exception as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    finally:
        xray_recorder.end_segment()

def post_json(url, data, target):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    curr_url = request.host
    segment = xray_recorder.begin_segment(name=curr_url)

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json() 
    except requests.RequestException as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    except Exception as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    finally:
        xray_recorder.end_segment()

def put_json(url, data, target):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    curr_url = request.host
    segment = xray_recorder.begin_segment(name=curr_url)

    try:
        print("ingresa al try")
        print(data)
        response = requests.put(url, json=data, headers=headers)
        print("14")
        #response_decode = json.loads(response.decode('utf8').replace("'", '"')) 
        print("decode")
        print(response)
        response.raise_for_status()
        print("finaliza al try")
        return response.json()  
    except requests.RequestException as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    except Exception as e:
        segment.add_exception(e, traceback.format_exc())
        raise
    finally:
        xray_recorder.end_segment()
