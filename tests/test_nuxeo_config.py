import os
import unittest
from unittest.mock import patch

from conf import conf


class NuxeoConfigTests(unittest.TestCase):
    @patch.object(conf, 'get_param', return_value='secret')
    def test_retries_are_bounded_below_gunicorn_timeout(self, _get_param):
        with patch.dict(os.environ, {
            'PARAMETER_STORE': 'test',
            'NUXEO_URL': 'http://nuxeo.test/'
        }):
            nuxeo = conf.init_nuxeo()

        allowed_methods = nuxeo.client.retries.allowed_methods
        self.assertEqual(nuxeo.client.retries.total, 2)
        self.assertNotIn('POST', allowed_methods)
        self.assertIn('GET', allowed_methods)
        self.assertIn('PUT', allowed_methods)
        self.assertIn('DELETE', allowed_methods)


if __name__ == '__main__':
    unittest.main()
