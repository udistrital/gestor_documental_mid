

import base64
import json
import logging
import os
import time
from flask import Response, abort, request
import requests
from nuxeo.models import Document, FileBlob
from nuxeo.exceptions import UploadError
from models.eval_doc_crud_res import obtener_respuesta
from models.firma import firmar
from models.firma_electronica import ElectronicSign
from models.utils import remove_duplicates
from nuxeo.client import Nuxeo

def getDocumentoNuxeoFormatted(uid, nuxeo: Nuxeo):
    doc = nuxeo.documents.get(uid = uid)
    DicRes = doc.properties
    blob_get = doc.fetch_blob()
    blob64 = base64.b64encode(blob_get)
    DicRes['file'] = str(blob64).replace("b'","'").replace("'","")
    return DicRes

def getOne(uid, nuxeo: Nuxeo):
    """
        Consulta 1 documento a Nuxeo mediante uid

        Parameters
        ----------
        uid : string
            uid de documento
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : documento en base64 y propiedades
    """
    try:
        resource = uid
        if resource is None:
            abort(404, description="Not found resource")

        if uid.count('-') != 4 or len(uid) != 36:
            abort(400, description="invalid parameter")

        res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)
        res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
        if str(res_json) != "[{}]":
            DicDoc = getDocumentoNuxeoFormatted(uid, nuxeo)
            return Response(json.dumps(DicDoc), status=200, mimetype='application/json')
        else:
            DicStatus = {
                'Status':'document not found',
                'Code':'404'
            }
            return Response(json.dumps(DicStatus), status=404, mimetype='application/json')
    except Exception as e:
        logging.error("type error: " + str(e))
        if '400' in str(e):
            DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
            return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
        return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

def post(body, nuxeo: Nuxeo):
    """
        Carga 1 documento (orientado a pdf) a Nuxeo pasando body json con archivo en base64 y parametros
        
        Parameters
        ----------
        body : json
            json con parametros como tipoDocumento, nombre, descripcion, metadatos, base64
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    response_array = []
    try:            
        data = body
        for i in range(len(data)):
            if len(str(data[i]['file'])) < 1000:
                error_dict = {
                    'Status':'invalid pdf file',
                    'Code':'400'
                }                
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            

            IdDocumento = data[i]['IdTipoDocumento']
            res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento))

            if res.status_code == 200:                
                res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                up_file = Document(
                name = data[i]['nombre'],
                type = res_json['TipoDocumentoNuxeo'],
                properties={
                    'dc:title': data[i]['nombre'],
                })
                file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
                # Create a batch
                batch = nuxeo.uploads.batch()
                blob = base64.b64decode(data[i]['file'])
                with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
                    fout.write(blob)
                try:
                    uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
                    #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                except UploadError:
                    return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                # Attach it to the file
                operation = nuxeo.operations.new('Blob.AttachOnDocument')
                #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
                operation.params = {'document': str(file.uid)}
                operation.input_obj = uploaded
                operation.execute()        
                firma_electronica = firmar(str(data[i]['file']))
                all_metadata = str({** firma_electronica, ** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')
                DicPostDoc = {
                    'Enlace' : str(file.uid),
                    'Metadatos' : all_metadata,
                    'Nombre' : data[i]['nombre'],
                    "Descripcion": data[i]['descripcion'],
                    'TipoDocumento' :  res_json,
                    'Activo': True
                }
                resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content
                dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                response_array.append(dictFromPost)
            else:
                return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
        dictFromPost = response_array if len(response_array) > 1 else dictFromPost
        return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
    except Exception as e:            
            logging.error("type error: " + str(e))
            if str(e) == "'IdTipoDocumento'":
                error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif str(e) == "'nombre'":
                error_dict = {'Status':'the field nombre is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(e) == "'file'":
                error_dict = {'Status':'the field file is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
            elif str(e) == "'metadatos'":                
                error_dict = {'Status':'the field metadatos is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif '400' in str(e):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

def postAny(body, nuxeo: Nuxeo):
    """
        Carga 1 documento de cualquier tipo a Nuxeo pasando body json con archivo en base64 y parametros
        
        Parameters
        ----------
        body : json
            json con parametros como tipoDocumento, nombre, descripcion, metadatos, base64
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    response_array = []
    try:            
        data = body
        for i in range(len(data)):
            if len(str(data[i]['file'])) < 1000:
                error_dict = {
                    'Status':'invalid pdf file',
                    'Code':'400'
                }                
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            

            IdDocumento = data[i]['IdTipoDocumento']
            res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento))

            if res.status_code == 200:                
                res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                up_file = Document(
                name = data[i]['nombre'],
                type = res_json['TipoDocumentoNuxeo'],
                properties={
                    'dc:title': data[i]['nombre'],
                })
                file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
                # Create a batch
                batch = nuxeo.uploads.batch()
                blob = base64.b64decode(data[i]['file'])
                filePath = 'document.' + data[i]['nombre'].split(".")[-1]
                with open(os.path.expanduser('./documents/'+ filePath), 'wb') as fout:
                    fout.write(blob)
                try:
                    uploaded = batch.upload(FileBlob('./documents/'+ filePath), chunked=True)
                except UploadError:
                    return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                # Attach it to the file
                operation = nuxeo.operations.new('Blob.AttachOnDocument')
                operation.params = {'document': str(file.uid)}
                operation.input_obj = uploaded
                operation.execute()        
                firma_electronica = firmar(str(data[i]['file']))
                all_metadata = str({** firma_electronica, ** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')
                DicPostDoc = {
                    'Enlace' : str(file.uid),
                    'Metadatos' : all_metadata,
                    'Nombre' : data[i]['nombre'],
                    "Descripcion": data[i]['descripcion'],
                    'TipoDocumento' :  res_json,
                    'Activo': True
                }
                resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content
                dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                response_array.append(dictFromPost)
            else:
                return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
        dictFromPost = response_array if len(response_array) > 1 else dictFromPost
        return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
    except Exception as e:            
            logging.error("type error: " + str(e))

            if str(e) == "'IdTipoDocumento'":
                error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif str(e) == "'nombre'":
                error_dict = {'Status':'the field nombre is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(e) == "'file'":
                error_dict = {'Status':'the field file is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
            elif str(e) == "'metadatos'":                
                error_dict = {'Status':'the field metadatos is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif '400' in str(e):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

def getAll(params, nuxeo: Nuxeo):
    """
        Consulta varios documentos a Nuxeo mediante query
        
        Parameters
        ----------
        params : MultiDict
            parametros como query, limit y offset
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : lista documentos en base64 y propiedades, como info de errores
    """
    try:
        querys = str(params.get('query')).split(';')
        querys = [query for query in querys if query != '']
        
        for i, query in enumerate(querys):
            if query.find('Activo') == -1:
                querys[i] = query + ',Activo:true'
            else:
                querys[i] = query.replace('Activo:false', 'Activo:true');
        
        querys = list(set(querys))

        limits = str(params.get('limit')).replace(',',';').split(';')

        if len(limits) > len(querys):
            limits = limits[:len(querys)]
        else:
            while len(limits) < len(querys):
                limits.append('10')
        for i, limit in enumerate(limits):
            if limit == '' or limit == 'None':
                limits[i] = '10'
        
        offsets = str(params.get('offset')).replace(',',';').split(';')

        if len(offsets) > len(querys):
            offsets = offsets[:len(querys)]
        else:
            while len(offsets) < len(querys):
                offsets.append('0')
        for i, offset in enumerate(offsets):
            if offset == '' or offset == 'None':
                offsets[i] = '0'
        
        urlsDocuments = []
        for i, query in enumerate(querys):
            urlsDocuments.append('?query='+query+'&limit='+limits[i]+'&offset='+offsets[i])

        listUUIDS = []
        listDocCrudErrors = []
        docCrudQueryCount = 0
        for url in urlsDocuments:
            res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento'+url+'&fields=Id,Enlace,Nombre&sortby=Id&order=asc')
            res_doc_crud = res_doc_crud.content.decode('utf8')
            try:
                res_json = obtener_respuesta(res_doc_crud)
                if res_json != [{}]:
                    listUUIDS += res_json
                    docCrudQueryCount+=1
            except Exception as e:
                listDocCrudErrors.append({"error":str(e),"url":url})

        if len(listUUIDS) == 0:
            if len(listDocCrudErrors) > 0:
                DicStatus = {
                    'Status':'Bad Request',
                    'Code':'400',
                    'Errors': listDocCrudErrors
                }
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            else:
                DicStatus = {
                    'Status':'Documents not found',
                    'Code':'404',
                    'Errors': listDocCrudErrors
                }
                return Response(json.dumps(DicStatus), status=404, mimetype='application/json')
        else:
            
            listUUIDS = remove_duplicates(listUUIDS)
            
            if len(listUUIDS) > 150: # 150 es aproximandamente el límite de uids que se pueden consultar al mismo tiempo con documents.query()
                DicStatus = {        # más allá de ese límite genera error de servidor en nuxeo (400 y 414) -> Request-URI Too Long
                    'Status':'Bad Request, documents list is too long > 150',
                    'Code':'400',
                    'Errors': listUUIDS
                }
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')

            query = "SELECT * FROM Document WHERE ecm:uuid IN ('{}')".format("', '".join([item["Enlace"] for item in listUUIDS]))
            doc = nuxeo.documents.query(opts= {'query':query})
            
            for i, f in enumerate(doc['entries']):
                for docList in listUUIDS:
                    if docList["Enlace"] == f.uid:
                        DicRes = f.properties
                        blob_get = f.fetch_blob()
                        blob64 = base64.b64encode(blob_get)
                        DicRes['file'] = str(blob64).replace("b'","'").replace("'","")
                        docList['Nuxeo'] = DicRes
                        break
            
            if docCrudQueryCount < len(urlsDocuments):
                status = 'Partially successful request, some query(s) returned nothing'
                if len(doc['entries']) < len(listUUIDS):
                    status += ', some document(s) were not found'
                DicStatus = {
                    'Status':status,
                    'Code':'206',
                    'Data':listUUIDS,
                    'Errors': listDocCrudErrors
                }
                return Response(json.dumps(DicStatus), status=206, mimetype='application/json')
            else:
                if len(doc['entries']) < len(listUUIDS):
                    DicStatus = {
                        'Status':'Partially successful request, some document(s) were not found',
                        'Code':'206',
                        'Data':listUUIDS,
                        'Errors': listDocCrudErrors
                    }
                    return Response(json.dumps(DicStatus), status=206, mimetype='application/json')
                else:
                    DicStatus = {
                        'Status':'Successful request',
                        'Code':'200',
                        'Data':listUUIDS,
                        'Errors': listDocCrudErrors
                    }
                    return Response(json.dumps(DicStatus), status=200, mimetype='application/json')
            
    except Exception as e:
        logging.error("type error: " + str(e))
        return Response(json.dumps({'Status':'Internal Error', 'Code':'500', 'Error':str(e)}), status=500, mimetype='application/json')
    
def postMetadata(uid, body, nuxeo: Nuxeo):
    """
        Carga de metadatos relacionados a Nuxeo pasando uid y body json con parametros
        
        Parameters
        ----------
        uid : string
            uid del documento
        body : json
            json con parametros de metadata
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    try:    
        if uid.count('-') != 4 or len(uid) != 36:                
            abort(400, description="invalid parameter")
        data = body            
        if data is None or str(data) == "{}" :
            DicStatus = {'Status':'invalid request body','Code':'400'}
            return Response(json.dumps(DicStatus), status=400, mimetype='application/json')        

        res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)    
        res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
        if str(res_json) != "[{}]": 
            try:    
                doc = nuxeo.documents.get(uid = uid)
                for prop, value in data['properties'].items():
                    doc.properties[prop] = value
                doc.save()
                return Response(json.dumps({'Status':'200'}), status=200, mimetype='application/json')
            except Exception as e:
                logging.error("type error: " + str(e))
                return Response(json.dumps({'Status':'500'}), status=500, mimetype='application/json')
        else:
            DicStatus = {'Status':'document not found', 'Code':'404'}
            return Response(json.dumps(DicStatus), status=404, mimetype='application/json')            
    except Exception as e:            
        logging.error("type error: " + str(e))
        if 'invalid parameter' in str(e):
            DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
            return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
        if '400' in str(e):
            DicStatus = {'Status':'invalid request body', 'Code':'400'}
            return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
        
        return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

def delete(uid, params, nuxeo: Nuxeo):
    """
        Borra 1 documento a Nuxeo mediante uid
        
        Parameters
        ----------
        uid : string
            uid de documento
        params : MultiDict
            parametro versionar para conservar o no el documento
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    try:                        
        versionar = params.get("versionar")
        versionar = False if versionar is None else eval(versionar.capitalize())

        if uid.count('-') != 4 or len(uid) != 36:                
            abort(400, description="invalid parameter")

        res_doc_crud = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento?query=Activo:true,Enlace:'+uid)    
        res_json = json.loads(res_doc_crud.content.decode('utf8').replace("'", '"'))
        if str(res_json) != "[{}]":
            objeto = {
                'Id': res_json[0]['Id'],
                'Nombre': res_json[0]['Nombre'],
                'Descripcion': res_json[0]['Descripcion'],
                'Enlace': res_json[0]['Enlace'],
                'TipoDocumento': res_json[0]['TipoDocumento'],
                'Metadatos': res_json[0]['Metadatos'],
                'Activo': False
            }
            res_del =  requests.put(str(os.environ['DOCUMENTOS_CRUD_URL']+'/documento/'+str(res_json[0]['Id'])), json=objeto )
            res_del_json = json.loads(res_del.content.decode('utf8').replace("'", '"'))
            DicStatus = {
                'doc_deleted': res_del_json['Id'],
                'nuxeo_doc_deleted': uid,
                'Status':'ok',
                'Code':'200'
            }
            if not versionar:
                doc = nuxeo.documents.get(uid = uid)
                doc.delete()
            return Response(json.dumps(DicStatus), status=200, mimetype='application/json')
        else:
            DicStatus = {
                'Status':'document not found',
                'Code':'404'
            }
            return Response(json.dumps(DicStatus), status=404, mimetype='application/json')
    except Exception as e:
        logging.error("type error: " + str(e))
        if '400' in str(e):
            DicStatus = {'Status':'invalid uid parameter', 'Code':'400'}
            return Response(json.dumps(DicStatus), status=400, mimetype='application/json')            
        return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')     

def postStoreDocument(body, nuxeo: Nuxeo):
    """
        Carga 1 documento a Nuxeo
        
        Parameters
        ----------
        body : json
            json con parametros
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    response_array = []
    try:
        data = body
        #Se hace un ciclo para iterar sobre el array que se recibe en formato json, se recibe uno normalmente
        for i in range(len(data)):
            #Se valida que sea un archivo en pdf
            if len(str(data[i]['file'])) < 1000:
                error_dict = {
                    'Status': 'Invalid pdf file',
                    'Code': '400'
                }
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')

            idTipoDocumento = data[i]['IdTipoDocumento']
            res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(idTipoDocumento))

            if res.status_code == 200:
                res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
                up_file_to_nuxeo = Document(
                    name = data[i]['nombre'],
                    type = res_json['TipoDocumentoNuxeo'],
                    properties = {
                        'dc:title': data[i]['nombre'],
                    }
                )

                file = nuxeo.documents.create(up_file_to_nuxeo, parent_path=str(res_json['Workspace']))

                batch = nuxeo.uploads.batch()
                blob = base64.b64decode(data[i]['file'])
                with open(os.path.expanduser('./documents/document.pdf'), 'wb') as fout:
                    fout.write(blob)
                try:
                    uploaded = batch.upload(FileBlob('./documents/document.pdf'), chunked=True)
                    #uploaded = batch.upload(BufferBlob(blob), chunked=True)
                except UploadError:
                    return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')
                # Attach it to the file
                operation = nuxeo.operations.new('Blob.AttachOnDocument')
                #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
                operation.params = {'document': str(file.uid)}
                operation.input_obj = uploaded
                operation.execute()

                metadata = str({** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')

                metadatos_to_documentos = {
                    'Enlace':       str(file.uid),
                    'Metadatos':    metadata,
                    'Nombre':       data[i]['nombre'],
                    "Descripcion":  data[i]['descripcion'],
                    'TipoDocumento':res_json,
                    'Activo':       True
                }
                
                resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=metadatos_to_documentos).content
                dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))                                        
                response_array.append(dictFromPost)

            else:
                return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')
        
        dictFromPost = response_array if len(response_array) > 1 else dictFromPost
        return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
    
    except Exception as exception:
            logging.error("type error: " + str(exception))
            if str(exception) == "'IdTipoDocumento'":
                error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}                
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif str(exception) == "'nombre'":
                error_dict = {'Status':'the field nombre is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(exception) == "'file'":
                error_dict = {'Status':'the field file is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')                                
            elif str(exception) == "'metadatos'":                
                error_dict = {'Status':'the field metadatos is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')            
            elif '400' in str(exception):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(exception)}), status=500, mimetype='application/json')

def postFirmaElectronica(body, nuxeo: Nuxeo):
    """
        Carga 1 documento (orientado a pdf) a Nuxeo pasando body json con archivo en base64
        y parametros como firmantes y representantes para estampado de firma electrónica en documento pdf

        Parameters
        ----------
        body : json
            json con parametros como tipoDocumento, nombre, descripcion, metadatos, base64, firmantes y representantes
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento
    """
    response_array = []
    try:
        data = body
        for i in range(len(data)):
            if len(str(data[i]['file'])) < 1000:
                error_dict = {
                    'Status':'invalid pdf file',
                    'Code':'400'
                }
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')

            IdDocumento = data[i]['IdTipoDocumento']
            res = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/tipo_documento/'+str(IdDocumento))

            if res.status_code != 200:
                return Response(json.dumps({'Status':'404','Error': str("the id "+str(data[i]['IdTipoDocumento'])+" does not exist in documents_crud")}), status=404, mimetype='application/json')

            res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
            up_file = Document(
            name = data[i]['nombre'],
            type = res_json['TipoDocumentoNuxeo'],
            properties={
                'dc:title': data[i]['nombre'],
            })

            file = nuxeo.documents.create(up_file, parent_path=str(res_json['Workspace']))
            # Create a batch
            batch = nuxeo.uploads.batch()
            blob = base64.b64decode(data[i]['file'])
            with open(os.path.expanduser('./documents/documentToSign.pdf'), 'wb') as fout:
                fout.write(blob)

            all_metadata = str({** data[i]['metadatos']}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"')

            DicPostDoc = {
                'Metadatos': all_metadata,
                'Nombre': data[i]['nombre'],
                "Descripcion": data[i]['descripcion'],
                'TipoDocumento':  res_json,
                'Activo': True
            }

            jsonFirmantes = {
                "firmantes": data[i]["firmantes"],
                "representantes": data[i]["representantes"],
            }

            resPost = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento', json=DicPostDoc).content
            responsePostDoc = json.loads(resPost.decode('utf8').replace("'", '"'))

            firma_electronica = firmar(str(data[i]['file']))

            electronicSign = ElectronicSign()
            # firma_completa = electronicSign.firmaCompleta(firma_electronica["llaves"]["firma"], responsePostDoc["Id"])
            objFirmaElectronica = {
                "Activo": True,
                "CodigoAutenticidad": firma_electronica["codigo_autenticidad"],
                "FirmaEncriptada": firma_electronica["llaves"]["firma"],
                "Firmantes": json.dumps(jsonFirmantes),
                "Llaves": json.dumps(firma_electronica["llaves"]),
                "DocumentoId": {"Id": responsePostDoc["Id"]},
            }

            reqPostFirma = requests.post(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/firma_electronica', json=objFirmaElectronica).content
            responsePostFirma = json.loads(reqPostFirma.decode('utf8').replace("'", '"'))

            datos = {
                "firma": responsePostFirma["Id"],
                "firmantes": data[i]["firmantes"],
                "representantes": data[i]["representantes"],
                "tipo_documento": res_json["Nombre"],
            }

            electronicSign.estamparFirmaElectronica(datos)
            jsonStringFirmantes = {
                "firmantes": json.dumps(data[i]["firmantes"]),
                "representantes": json.dumps(data[i]["representantes"])
            }

            all_metadata = str({** firma_electronica, ** data[i]['metadatos'],  ** jsonStringFirmantes}).replace("{'", '{\\"').replace("': '", '\\":\\"').replace("': ", '\\":').replace(", '", ',\\"').replace("',", '",').replace('",' , '\\",').replace("'}", '\\"}').replace('\\"', '\"').replace("[", "").replace("]", "").replace('"{', '{').replace('}"', '}').replace(": ", ":").replace(", ", ",").replace("[", "").replace("]", "").replace("},{", ",")

            DicPostDoc = {
                'Metadatos': all_metadata,
                "enlace": str(file.uid),
                "firmantes": data[i]["firmantes"],
                "representantes": data[i]["representantes"],
                'Nombre': data[i]['nombre'],
                "Descripcion": data[i]['descripcion'],
                'TipoDocumento' :  res_json,
                'Activo': True
            }

            try:
                uploaded = batch.upload(FileBlob('./documents/documentSignedFlattened.pdf'), chunked=True)
                #uploaded = batch.upload(BufferBlob(blob), chunked=True)
            except UploadError:
                return Response(json.dumps({'Status':'500','Error':UploadError}), status=200, mimetype='application/json')

            # Attach it to the file
            operation = nuxeo.operations.new('Blob.AttachOnDocument')
            #operation.params = {'document': str(res_json['Workspace'])+'/'+data[i]['nombre']}
            operation.params = {'document': str(file.uid)}
            operation.input_obj = uploaded
            operation.execute()
            resPost = requests.put(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/documento/' + str(responsePostDoc["Id"]), json=DicPostDoc).content

            dictFromPost = json.loads(resPost.decode('utf8').replace("'", '"'))
            response_array.append(dictFromPost)

        dictFromPost = response_array if len(response_array) > 1 else dictFromPost
        return Response(json.dumps({'Status':'200', 'res':dictFromPost}), status=200, mimetype='application/json')
    except Exception as e:
            logging.error("type error: " + str(e))

            if str(e) == "'IdTipoDocumento'":
                error_dict = {'Status':'the field IdTipoDocumento is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(e) == "'nombre'":
                error_dict = {'Status':'the field nombre is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(e) == "'file'":
                error_dict = {'Status':'the field file is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif str(e) == "'metadatos'":
                error_dict = {'Status':'the field metadatos is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif '400' in str(e):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')

def postVerify(body, nuxeo: Nuxeo):
    """
        Verificar firma electrónica de documentos (pdf) cargados y firmados digitalmente,

        Parameters
        ----------
        body : json
            json con hash de firma electrónica
        nuxeo : Nuxeo
            cliente nuxeo

        Return
        ----------
        json : info documento si existe firma electrónica
    """
    response_array = []
    try:
        data = body
        for i in range(len(data)):

            resFirma = requests.get(str(os.environ['DOCUMENTOS_CRUD_URL'])+'/firma_electronica/'+str(data[i]["firma"]))

            if resFirma.status_code != 200:
                return Response(resFirma, resFirma.status_code, mimetype='application/json')

            responseGetFirma = json.loads(resFirma.content.decode('utf8').replace("'", '"'))
            firma = responseGetFirma["FirmaEncriptada"].encode()

            if "firma" not in responseGetFirma["DocumentoId"]["Metadatos"]:
                error_dict = {'Status': "document not signed", 'code': '404'}
                return Response(json.dumps(error_dict), status=404, mimetype='application/json')
            elif firma in responseGetFirma["DocumentoId"]["Metadatos"].encode():
                responseNuxeo = getDocumentoNuxeoFormatted(responseGetFirma["DocumentoId"]["Enlace"], nuxeo)
                # succes_dict = {'Status': responseNuxeo, 'code': '200'}
                # return Response(json.dumps(succes_dict), status=200, mimetype='application/json')
                response_array.append(responseNuxeo)
            else:
                error_dict = {'Status': "electronic signatures do not match", 'code': '404'}
                return Response(json.dumps(error_dict), status=404, mimetype='application/json')

        return Response(json.dumps({'Status':'200', 'res':response_array}), status=200, mimetype='application/json')
    except Exception as e:
            logging.error("type error: " + str(e))
            if str(e) == "'firma'":
                error_dict = {'Status':'the field firma is required','Code':'400'}
                return Response(json.dumps(error_dict), status=400, mimetype='application/json')
            elif '400' in str(e):
                DicStatus = {'Status':'invalid request body', 'Code':'400'}
                return Response(json.dumps(DicStatus), status=400, mimetype='application/json')
            return Response(json.dumps({'Status':'500','Error':str(e)}), status=500, mimetype='application/json')
