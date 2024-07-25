import traceback
import requests
import json
import io
import logging
from aws_xray_sdk.core import xray_recorder

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

def send_json(url, method, target, datajson=None):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    segment = xray_recorder.begin_segment(name="send_json")

    try:
        response = requests.request(method, url, json=datajson, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response.json() if target is None else json.loads(response.text, object_hook=target)
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise

def send_json_escape_unicode(url, method, target, datajson=None):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    segment = xray_recorder.begin_segment(name="send_json_escape_unicode")

    try:
        datajson = json.dumps(datajson, ensure_ascii=False) if datajson else None
        response = requests.request(method, url, data=datajson, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response.json() if target is None else json.loads(response.text, object_hook=target)
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise

def get_json(url, target):
    headers = {
        "Authorization": get_header(),
        "Accept": "application/json"
    }
    print("UARA ", url)
    # Crear un subsegmento dentro del contexto del segmento principal
    with xray_recorder.in_subsegment('get_json') as segment:
        try:
            print(url)
            response = requests.get(url, headers=headers)
            print(response)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error reading response: {e}")
            segment.add_exception(e, traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            segment.add_exception(e, traceback.format_exc())
            raise

def get_json_wso2(url, target):
    headers = {
        "Accept": "application/json"
    }
    segment = xray_recorder.begin_segment(name="get_json_wso2")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response.json() if target is None else json.loads(response.text, object_hook=target)
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise

def get_json_test(url, target):
    headers = {
        "Accept": "application/json"
    }
    segment = xray_recorder.begin_segment(name="get_json_test")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response, json.loads(response.text, object_hook=target)
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise

def get_xml(url, target):
    headers = {
        "Accept": "application/xml"
    }
    segment = xray_recorder.begin_segment(name="get_xml")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response.text if target is None else xml.loads(response.text, object_hook=target)
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise

def get_xml2string(url):
    headers = {
        "Accept": "application/xml"
    }
    segment = xray_recorder.begin_segment(name="get_xml2string")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        xray_recorder.end_segment()

        return response.text.strip()
    except requests.RequestException as e:
        logger.error(f"Error reading response: {e}")
        xray_recorder.end_segment()
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        xray_recorder.end_segment()
        raise
