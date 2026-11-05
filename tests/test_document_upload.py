import base64
import hashlib
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('BUCKET_NAME', 'test-bucket')
os.environ.setdefault('DOCUMENTOS_CRUD_URL', 'http://documentos-crud.test/v1/')

from controllers import document
from flask import Flask, request
from nuxeo.exceptions import UploadError


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            'TipoDocumentoNuxeo': 'File',
            'Workspace': '/default-domain/workspaces/test'
        }


class FakeDocument:
    uid = '12345678-1234-1234-1234-123456789012'


class FakeDocuments:
    def __init__(self, events):
        self.events = events
        self.deleted = []

    def create(self, _document, parent_path):
        self.events.append(('create', parent_path))
        return FakeDocument()

    def delete(self, uid):
        self.deleted.append(uid)


class FakeBatch:
    def __init__(self, events, upload_errors=None):
        self.events = events
        self.upload_errors = list(upload_errors or [])
        self.cancelled = False
        self.path = None
        self.digest = None
        self.name = None

    def upload(self, blob, chunked):
        self.path = blob.path
        self.name = blob.name
        with open(blob.path, 'rb') as uploaded_file:
            content = uploaded_file.read()
        self.digest = hashlib.sha256(content).hexdigest()
        self.events.append(('upload', len(content), chunked))
        if self.upload_errors:
            raise self.upload_errors.pop(0)
        return object()

    def cancel(self):
        self.cancelled = True


class FakeUploads:
    def __init__(self, batch):
        self.current_batch = batch

    def batch(self):
        return self.current_batch


class FakeOperation:
    def __init__(self, events, execute_error=None):
        self.events = events
        self.execute_error = execute_error
        self.params = None
        self.input_obj = None

    def execute(self):
        self.events.append(('attach', self.params['document']))
        if self.execute_error:
            raise self.execute_error


class FakeOperations:
    def __init__(self, events, execute_error=None):
        self.events = events
        self.execute_error = execute_error

    def new(self, name):
        self.events.append(('operation', name))
        return FakeOperation(self.events, self.execute_error)


class FakeNuxeo:
    def __init__(self, upload_errors=None, execute_error=None):
        self.events = []
        self.batch = FakeBatch(self.events, upload_errors)
        self.uploads = FakeUploads(self.batch)
        self.documents = FakeDocuments(self.events)
        self.operations = FakeOperations(self.events, execute_error)


class DocumentUploadTests(unittest.TestCase):
    @staticmethod
    def body(content):
        return [{
            'IdTipoDocumento': 1,
            'nombre': 'datos.xlsx',
            'descripcion': 'Prueba',
            'metadatos': {},
            'file': base64.b64encode(content).decode('ascii')
        }]

    @patch.object(document, 'post_json', return_value={'Id': 1})
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_large_upload_preserves_content_and_removes_temporary_file(
        self, _get_json, _firmar, _post_json
    ):
        content = os.urandom(6 * 1024 * 1024)
        nuxeo = FakeNuxeo()

        response = document.postAny(self.body(content), nuxeo)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            nuxeo.batch.digest,
            hashlib.sha256(content).hexdigest()
        )
        self.assertFalse(os.path.exists(nuxeo.batch.path))
        self.assertEqual(nuxeo.events[0][0], 'upload')
        self.assertEqual(nuxeo.events[1][0], 'create')
        self.assertEqual(nuxeo.batch.name, 'datos.xlsx')
        self.assertFalse(nuxeo.batch.cancelled)

    @patch.object(document, 'post_json', return_value={'Id': 1})
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_large_json_request_is_processed_over_http(
        self, _get_json, _firmar, _post_json
    ):
        content = os.urandom(4 * 1024 * 1024)
        payload = self.body(content)
        nuxeo = FakeNuxeo()
        app = Flask(__name__)

        @app.post('/v1/document/uploadAnyFormat')
        def upload():
            return document.postAny(request.get_json(), nuxeo)

        with app.test_client() as client:
            response = client.post('/v1/document/uploadAnyFormat', json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(json.dumps(payload).encode('utf-8')), 5 * 1024 * 1024)
        self.assertEqual(
            nuxeo.batch.digest,
            hashlib.sha256(content).hexdigest()
        )

    @patch.object(document, 'post_json', return_value={'Id': 1})
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_interrupted_chunked_upload_resumes_the_same_batch(
        self, _get_json, _firmar, _post_json
    ):
        upload_error = UploadError('datos.xlsx', chunk=0, info='500')
        nuxeo = FakeNuxeo(upload_errors=[upload_error])

        response = document.postAny(self.body(os.urandom(1024)), nuxeo)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [event[0] for event in nuxeo.events].count('upload'),
            2
        )
        self.assertFalse(nuxeo.batch.cancelled)

    @patch.object(document, 'post_json', return_value={'Id': 1})
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_nuxeo_upload_error_returns_502_and_cleans_up(
        self, _get_json, _firmar, _post_json
    ):
        upload_error = UploadError('datos.xlsx', info='503')
        nuxeo = FakeNuxeo(upload_errors=[upload_error] * 3)

        response = document.postAny(self.body(os.urandom(1024)), nuxeo)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(json.loads(response.data)['Status'], '502')
        self.assertTrue(nuxeo.batch.cancelled)
        self.assertFalse(os.path.exists(nuxeo.batch.path))
        self.assertEqual(nuxeo.documents.deleted, [])

    @patch.object(document, 'post_json', return_value={'Id': 1})
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_attach_error_rolls_back_document_batch_and_temporary_file(
        self, _get_json, _firmar, _post_json
    ):
        nuxeo = FakeNuxeo(execute_error=RuntimeError('attach failed'))

        response = document.postAny(self.body(os.urandom(1024)), nuxeo)

        self.assertEqual(response.status_code, 500)
        self.assertTrue(nuxeo.batch.cancelled)
        self.assertFalse(os.path.exists(nuxeo.batch.path))
        self.assertEqual(nuxeo.documents.deleted, [FakeDocument.uid])

    @patch.object(document, 'post_json', side_effect=RuntimeError('response lost'))
    @patch.object(document, 'firmar', return_value={})
    @patch.object(document, 'get_json', return_value=FakeResponse())
    def test_ambiguous_crud_error_does_not_delete_attached_document(
        self, _get_json, _firmar, _post_json
    ):
        nuxeo = FakeNuxeo()

        response = document.postAny(self.body(os.urandom(1024)), nuxeo)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(nuxeo.documents.deleted, [])
        self.assertTrue(nuxeo.batch.cancelled)


if __name__ == '__main__':
    unittest.main()
