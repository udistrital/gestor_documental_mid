import os
from flask import Flask
from conf import conf
from conf.logging_json import setup_json_logging
from routers import router
from controllers import error
from xray_python.xray import init_xray

setup_json_logging()

conf.checkEnv()
nuxeo = conf.init_nuxeo()
app = Flask(__name__)

init_xray(app)

router.addRouting(app, nuxeo)
error.add_error_handler(app)

if __name__ == '__main__':
    
    #app.debug = True
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))

