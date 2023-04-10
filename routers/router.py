


from flask import Blueprint, request
from flask_restx import Api, Resource
from controllers import healthCheck, document
from models.model_params import define_parameters
from flask_cors import CORS, cross_origin
from conf.conf import api_cors_config
from nuxeo.client import Nuxeo

nuxeo = None

def addRouting(app, nuxeoInit: Nuxeo):
    global nuxeo
    nuxeo = nuxeoInit
    app.register_blueprint(healthCheckController)
    app.register_blueprint(documentController, url_prefix='/v1')


healthCheckController = Blueprint('healthCheckController', __name__, url_prefix='/v1')
CORS(healthCheckController)

@healthCheckController.route('/')
def _():
    return healthCheck.healthCheck(nuxeo, documentDoc)


documentController = Blueprint('documentController', __name__)
CORS(documentController)
documentDoc = Api(documentController, version='1.0', title='gestor_documental_mid', description='Api mid para la autenticacion de documentos en Nuxeo', doc="/swagger")

documentNamespaceController = documentDoc.namespace("document", description="Nuxeo document operations")

model_params = define_parameters(documentDoc)

@documentNamespaceController.route('/<string:uid>', doc={'params':{'uid': 'UID del documento generado en Nuxeo'}})
class documentGetOne_DeleteOne(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    }) 
    @cross_origin(**api_cors_config)
    def get(self, uid):
        """
            Permite consultar documento por uid.

            Parameters
            ----------
            request : uid

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        return document.getOne(uid, nuxeo)

    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    }) 
    @documentNamespaceController.expect(model_params['query_parser'])
    @cross_origin(**api_cors_config)
    def delete(self, uid):
        """
            Permite borrar documento por uid.

            Parameters
            ----------
            request : uid, versionar

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        params = request.args
        return document.delete(uid, params, nuxeo)

@documentNamespaceController.route('/upload')
class documentPost(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=model_params['upload_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self):
        """
            Permite subir documento.

            Parameters
            ----------
            request : json
                Json Body {Document}, Documento que será subido a nuxeo

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.post(body, nuxeo)

@documentNamespaceController.route('/uploadAnyFormat')
class documentPostAnyFormat(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=model_params['upload_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self):
        """
            Permite subir cualquier tipo de documento, de acuerdo a la extensión de su nombre.

            Parameters
            ----------
            request : json
                Json Body {Document}, Documento que será subido a nuxeo

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.postAny(body, nuxeo)

@documentNamespaceController.route('/', doc={'params':{'query': 'Query similar to documentos_crud', 'limit': 'limit similar a documentos_crud', 'offset': 'offset similar a documentos_crud'}})
class documentGetAll(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        206: 'Partial Content',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    })    
    @cross_origin(**api_cors_config)
    def get(self):
        """
            Permite consultar listado de documentos, usando como contexto de busqueda la tabla documento de documentos_crud.

            Parameters
            ----------
            Request : ?query=params&limit=values&offset=values
                query: usa la misma métodologia de consulta que en apis beego, e.j: ?query=Nombre:doc...
                        - para lista de documentos use parametro__in:valor1|valor2|...|valorn e.j: Id__in:2|3|4
                        - puede anida querys separandolos por ';' si requiere varias consultas con distintos parametros, e.j: Id:2;Nombre:contrato
                limit & offset: son opcionales, limit defecto a 10 y offset a 0
                - si anida querys, y usa offset o limit debe haber un valor para cada query separados por ';' o ','
                - e.j: ?query=Id:2;Nombre:contrato&limit=1;10&offset=0;5
                Nota: procure evitar uso de 0 o -1 para limit, si no conoce la cantidad de documentos.

            Returns
            -------
            Response : json
                Respuesta con Status, Code, Data y Errors en formato json
        """
        params = request.args
        return document.getAll(params, nuxeo)

@documentNamespaceController.route('/<string:uid>/metadata', doc={'params':{'uid': 'UID del documento generado en Nuxeo'}})
class documentPostMetadata(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        404: 'Not found',
        400: 'Bad request'
    },body=model_params['metadata_dublin_core_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self, uid):
        """
            Permite cargar metadata relacionada a documento.

            Parameters
            ----------
            request : uid, json
                uid del documento
                Json Body {Metadata}, metadata

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.postMetadata(uid, body, nuxeo)

@documentNamespaceController.route('/store_document')
class documentPostStoreDocument(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    },body=model_params['upload_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self):
        """
            Permite subir documento.

            Parameters
            ----------
            request : json
                Json Body {Document}, Documento que será subido a nuxeo

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.postStoreDocument(body, nuxeo)
    
@documentNamespaceController.route('/firma_electronica')
class documentPostFirmaElectronica(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=model_params['upload_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self):
        """
            Permite subir documento pdf y ser firmado electrónicamente.

            Parameters
            ----------
            request : json
                Json Body {Document}, Documento que será subido a nuxeo y firmantes

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.postFirmaElectronica(body, nuxeo)

@documentNamespaceController.route('/verify')
class documentPostVerify(Resource):
    @documentDoc.doc(responses={
        200: 'Success',
        500: 'Nuxeo error',
        400: 'Bad request'
    }, body=model_params['upload_model'])
    @documentNamespaceController.expect(model_params['request_parser'])
    @cross_origin(**api_cors_config)
    def post(self):
        """
            permite verificar la firma electronica de un documento

            Parameters
            ----------
            request : json
                Json Body {firma}, firma electronica encriptada con el id

            Returns
            -------
            Response
                Respuesta con cuerpo, status y en formato json
        """
        body = request.get_json()
        return document.postVerify(body)