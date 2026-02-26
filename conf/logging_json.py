import json
import logging
import os
import sys
import time
from flask import has_request_context, g, request

class UidContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.uid = getattr(g, "uid", None)
            record.path = request.path
            record.method = request.method
        else:
            record.uid = None
            record.path = None
            record.method = None
        return True

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "Fecha": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "Uid": getattr(record, "uid", None),
            "Metodo": getattr(record, "method", None),
            "Ruta": getattr(record, "path", None),
            "Mensaje": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_json_logging():
    root = logging.getLogger()

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level_name, logging.INFO))

    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        root.addHandler(h)

    for h in root.handlers:
        h.addFilter(UidContextFilter())
        h.setFormatter(JsonFormatter())

    # No mostrar logs de:
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("aws_xray_sdk").setLevel(logging.CRITICAL)
    logging.getLogger("nuxeo").setLevel(logging.WARNING)