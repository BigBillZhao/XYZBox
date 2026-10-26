"""HTTP boundary tests using a fake engine; never enumerate or touch disks."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock

from .server import Handler


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.engine = Mock(repository=Path('/mnt/fake'))
        self.engine.jobs.return_value = []
        self.engine.drives.return_value = [{'device': '/dev/nvme0n1', 'eligible': False}]
        self.engine.images.return_value = []
        self.engine.repository_online.return_value = True
        self.engine.submit.return_value = {'id': 'fake-job', 'status': 'queued'}
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.engine = self.engine
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        self.addCleanup(connection.close)
        connection.request(method, path, body=body, headers=headers or {})
        result = connection.getresponse()
        content = result.read()
        return result.status, content

    def test_state_exposes_system_disk_as_locked(self):
        status, body = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['drives'][0]['eligible'])

    def test_external_host_is_rejected(self):
        status, _ = self.request('GET', '/api/state', headers={'Host': 'evil.example'})
        self.assertEqual(status, 403)
        self.engine.drives.assert_not_called()

    def test_cross_site_and_plain_form_cannot_create_job(self):
        for headers in ({'Content-Type': 'application/json'},
                        {'Content-Type': 'application/x-www-form-urlencoded', 'X-XYZBox-Request': '1'},
                        {'Content-Type': 'application/json', 'X-XYZBox-Request': '1', 'Origin': 'http://evil.example'}):
            status, _ = self.request('POST', '/api/jobs', '{}', headers)
            self.assertEqual(status, 403)
        self.engine.submit.assert_not_called()

    def test_valid_local_json_is_passed_to_engine(self):
        payload = {'operation': 'capture', 'device': '/dev/sdz', 'serial': 'FAKE'}
        status, body = self.request('POST', '/api/jobs', json.dumps(payload),
                                    {'Content-Type': 'application/json', 'X-XYZBox-Request': '1'})
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)['job']['id'], 'fake-job')
        self.engine.submit.assert_called_once_with(payload)

    def test_invalid_json_and_engine_rejections_are_not_success(self):
        headers = {'Content-Type': 'application/json', 'X-XYZBox-Request': '1'}
        status, _ = self.request('POST', '/api/jobs', '[]', headers)
        self.assertEqual(status, 409)
        self.engine.submit.side_effect = RuntimeError('Wrong SSD serial')
        status, body = self.request('POST', '/api/jobs', '{}', headers)
        self.assertEqual(status, 409)
        self.assertIn(b'Wrong SSD serial', body)


if __name__ == '__main__':
    unittest.main()
