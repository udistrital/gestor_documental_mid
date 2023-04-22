

import json


def obtener_respuesta(response):
    if response.startswith('\n<!DOCTYPE html>'):
        empiezaEn = response.find('<h2>')
        terminaEn = response.find('</h2>', empiezaEn)
        if empiezaEn == -1 or terminaEn == -1:
            raise ValueError("It is not json, but html")
        else:
            errorInfo = response[empiezaEn+4:terminaEn]
            raise ValueError(errorInfo)
    else:
        res_json = json.loads(response.replace("'", '"'))
        if isinstance(res_json, dict):
            if "System" in res_json:
                raise ValueError(res_json["System"]["Message"])
            elif "Body" in res_json:
                raise ValueError(res_json["Body"])
            else:
                raise ValueError("Unknown error :(")
        else:
            return res_json