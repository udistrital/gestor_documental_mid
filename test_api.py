import os
import unittest
import base64
import json
import requests
import pprint

class Testeo(unittest.TestCase):
    URL = "http://0.0.0.0:8080/v1/"
    documentos_crud_url = str(os.environ['DOCUMENTOS_CRUD_URL'])
    nombre_doc = "prueba_core_2021_3"
    with open('test_blob.txt', 'r') as f:
        blob=f.read()#lee el archivo en base64
    upload_document = [{
        "IdTipoDocumento": 19,
        "nombre": "prueba_core_2021_3",
        "metadatos": {
            "dato1": "prueba 1",
            "dato2": "4 3 5",
            "dato3": "true"
        },
        "descripcion": "pruebas unitarias",
        "file": blob
    }]
    metadatos = {
        "properties":{
            "dc:description": "example",
            "dc:source":"prueba metadatos 2021",
            "dc:publisher": "cristian alape",
            "dc:rights": "Universidad Distrital Francisco José de Caldas",
            "dc:title": "prueba_core_2021_3",
            "dc:language": "Español",
            "nxtag:tags": [
                    {"label": "etiqueta_2","username": "desarrollooas"},
                    {"label": "etiqueta_2","username": "desarrollooas"},
                    {"label": "etiqueta_3","username": "desarrollooas"},
                    {"label": "etiqueta_4","username": "desarrollooas"},
                    {"label": "etiqueta_5","username": "desarrollooas"},
                    {"label": "etiqueta_6","username": "desarrollooas"},
                    {"label": "etiqueta_7","username": "desarrollooas"}
            ]
        }
    }
    uid_nuxeo_test = "705869ba-c618-4b0c-ae1d-980afe054941"#uid de prueba puede ser eliminado en un futuro

    def test_nuxeo_ok(self):
        res = requests.get(self.URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()),2)
        pprint.pprint("Nuxeo healthcheck: ok ")

    def test_nuxeo_fail(self):
        res = requests.get(self.URL)
        self.assertEqual(res.status_code, 500)
        self.assertEqual(len(res.json()),2)
        pprint.pprint("Nuxeo healthcheck fail: ok ")

    def test_documentos_crud_ok(self):
        res = requests.get(str(self.documentos_crud_url+"/documento"))
        self.assertEqual(res.status_code, 200)
        #self.assertEqual(len(res.json()), 2)
        pprint.pprint("documentos_crud service active: ok")

    def test_documentos_crud_404(self):
        res = requests.get(str(self.documentos_crud_url+"/documento123"))
        self.assertEqual(res.status_code, 404)
        #self.assertEqual(len(res.json()), 2)
        pprint.pprint("documentos_crud url not found: ok")

    def test_documentos_crud_500(self):
        res = requests.get(str(self.documentos_crud_url+"/documento"))
        self.assertEqual(res.status_code, 500)
        #self.assertEqual(len(res.json()), 2)
        pprint.pprint("documentos_crud service fail: ok")

    def test_documentos_crud_query(self):
        res = requests.get(str(self.documentos_crud_url+"/documento?query=Nombre:"+self.nombre_doc))
        self.assertEqual(res.status_code, 200)
        #self.assertEqual(len(res.json()), 2)
        pprint.pprint("documentos_crud query: ok")

    def test_documentos_crud_query_fail(self):
        res = requests.get(str(self.documentos_crud_url+"/documento?query=Nombre:"+self.nombre_doc+"123"))
        res_json = json.loads(res.content.decode('utf8').replace("'", '"'))
        self.assertEqual(str(res_json), "[{}]")
        #self.assertEqual(len(res.json()), 2)
        pprint.pprint("documentos_crud query fail: ok")

    def test_nuxeo_upload_document(self):
        res = requests.post(str(self.URL+"document/upload"), json=self.upload_document )        
        self.assertEqual(res.status_code, 200)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo upload document: ok")

    def test_nuxeo_upload_document_fail(self):
        res = requests.post(str(self.URL+"document/upload"), json=self.metadatos )        
        self.assertEqual(res.status_code, 500)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo upload document fail: ok")

    def test_nuxeo_get_document(self):
        res = requests.get(str(self.URL+"document/"+self.uid_nuxeo_test))
        self.assertEqual(res.status_code, 200)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo get document: ok")

    def test_nuxeo_get_document_fail(self):
        res = requests.get(str(self.URL+"document/"+self.uid_nuxeo_test+"123"))
        self.assertEqual(res.status_code, 500)#nuxeo no devuelve codigos 404
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo get document fail: ok")

    def test_nuxeo_post_metadata(self):
        res = requests.post(str(self.URL+"document/"+self.uid_nuxeo_test+"/metadata"), json=self.metadatos)
        self.assertEqual(res.status_code, 200)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo post metadata: ok")

    def test_nuxeo_post_metadata_fail(self):
        res = requests.post(str(self.URL+"document/"+self.uid_nuxeo_test+"/metadata"+"123"), json=self.metadatos)
        self.assertEqual(res.status_code, 404)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo post metadata fail: ok")

    def test_nuxeo_delete_document(self):
        res = requests.delete(str(self.URL+"document/"+self.uid_nuxeo_test))
        self.assertEqual(res.status_code, 200)
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo document delete: ok")

    def test_nuxeo_delete_document_fail(self):
        res = requests.delete(str(self.URL+"document/"+self.uid_nuxeo_test+"123"))
        self.assertEqual(res.status_code, 500)#nuxeo no devuelve 404
        #self.assertDictEqual(res.json, self.upload_document)
        pprint.pprint("Nuxeo document delete fail: ok")


if __name__ == "__main__":
    test = Testeo()
    #test.test_nuxeo_ok()
    #test.test_nuxeo_fail()
    #test.test_documentos_crud_ok()
    #test.test_documentos_crud_404()
    #test.test_documentos_crud_500()
    #test.test_documentos_crud_query()
    #test.test_documentos_crud_query_fail()
    #test.test_nuxeo_upload_document()
    #test.test_nuxeo_upload_document_fail()
    #test.test_nuxeo_get_document()
    #test.test_nuxeo_get_document_fail()
    #test.test_nuxeo_post_metada()
    #test.test_nuxeo_delete_document()
    test.test_nuxeo_delete_document_fail()
