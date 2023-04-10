import os
from flask import Flask
from conf import conf
from routers import router
from controllers import error
conf.checkEnv()

nuxeo = conf.init_nuxeo()
app = Flask(__name__)

router.addRouting(app, nuxeo)
error.add_error_handler(app)

#print(app.url_map)

if __name__ == '__main__':
    
    #app.debug = True
    app.run(host='0.0.0.0', port=int(os.environ['API_PORT']))

