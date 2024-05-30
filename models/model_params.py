

from flask_restx import reqparse, fields

def define_parameters(api):

    request_parser = reqparse.RequestParser(bundle_errors=True)
    request_parser.add_argument('list', location='json', type=list, required=True)
    query_parser = reqparse.RequestParser()
    query_parser.add_argument('versionar', type=bool, help='Conservar documento en Nuxeo?', default=False)
    
    metadata_doc_crud_model = api.model('documentos_crud_metadata', {
        'dato_a': fields.String,
        'dato_b': fields.String,
        'dato_n': fields.String
    })

    nuxeo_tags = api.model('nuxeo_tags', {
        'label': fields.String,
        'username': fields.String
    })

    properties = api.model('Metadata_properties', {
        'dc:description': fields.String,
        'dc:source': fields.String,
        'dc:publisher': fields.String,
        'dc:rights': fields.String,
        'dc:title': fields.String,
        'dc:language': fields.String,
        'nxtag:tags': fields.Nested(nuxeo_tags,as_list=True)
    })
    
    metadata_dublin_core_model = api.model('Nuxeo_dublin_core_metadata', {
        'properties': fields.Nested(properties)
    })
    
    upload_model = [api.model('upload_resquest', {
        'IdTipoDocumento': fields.Integer,
        'nombre': fields.String,
        #'metadatos': fields.String(default='{}'),
        'metadatos': fields.Nested(metadata_doc_crud_model),
        'descripcion': fields.String,
        'file': fields.String,
    })]

    put_update_model = [api.model('put_update_resquest', {
        'IdTipoDocumento': fields.Integer,
        'nombre': fields.String,
        'metadatos': fields.String,
        'descripcion': fields.String,
        'file': fields.String,
        'idDocumento': fields.Integer,
    })]

    return {k: v for k, v in vars().items() if not k.startswith('__')}