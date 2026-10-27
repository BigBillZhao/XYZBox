#!/usr/bin/env python3
"""Local-only XYZBox disk imaging UI. Disk operations live in core.Engine."""
import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from urllib.parse import urlsplit

try:
    from .core import Engine
except ImportError:
    from core import Engine

STATIC = Path(__file__).with_name('static')
ASSETS = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
          '/styles.css': ('styles.css', 'text/css'), '/app.js': ('app.js', 'text/javascript')}


class Handler(BaseHTTPRequestHandler):
    server_version = 'XYZBoxImager/0.1'

    def _local_request(self):
        try:
            host = urlsplit('http://' + self.headers.get('Host', '')).hostname
            return host in ('localhost', '127.0.0.1', '::1')
        except ValueError:
            return False

    def _respond(self, code, body, mime='application/json'):
        if mime == 'application/json':
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._local_request():
            return self._respond(403, {'error': '请从本机 localhost 打开工作站。'})
        path = urlsplit(self.path).path
        if path in ASSETS:
            name, mime = ASSETS[path]
            return self._respond(200, (STATIC / name).read_bytes(), mime)
        if path == '/api/state':
            try:
                preview = getattr(self.server, 'preview_state', None)
                if preview:
                    data = json.loads(Path(preview).read_text())
                    data['station'].update(preview=True, repository_online=False, busy=False)
                    return self._respond(200, data)
                engine = self.server.engine
                jobs = engine.jobs()
                return self._respond(200, {
                    'station': {'hostname': socket.gethostname(), 'repository': str(engine.repository),
                                'repository_online': engine.repository_online(),
                                'busy': any(j['status'] in ('queued', 'running') for j in jobs)},
                    'drives': engine.drives(), 'images': engine.images(), 'jobs': jobs})
            except Exception as exc:
                logging.exception('state request failed')
                return self._respond(503, {'error': str(exc)})
        return self._respond(404, {'error': 'Not found'})

    def do_POST(self):
        if getattr(self.server, 'preview_state', None):
            return self._respond(403, {'error': '这是只读历史预览，不能执行磁盘操作。'})
        if not self._local_request():
            return self._respond(403, {'error': '仅允许本机访问。'})
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self._respond(403, {'error': '跨站请求已拒绝。'})
        if self.headers.get('X-XYZBox-Request') != '1' or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self._respond(403, {'error': '缺少本机请求标识。'})
        if self.path != '/api/jobs':
            return self._respond(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                raise ValueError('请求长度无效。')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('请求必须为 JSON 对象。')
            return self._respond(202, {'job': self.server.engine.submit(payload)})
        except (ValueError, RuntimeError, KeyError) as exc:
            return self._respond(409, {'error': str(exc)})
        except Exception as exc:
            logging.exception('job submission failed')
            return self._respond(500, {'error': str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8830)
    parser.add_argument('--repository', default='/mnt/xyzbox-nas/XYZBoxImages')
    parser.add_argument('--state-dir', default='/var/lib/xyzbox-imager')
    parser.add_argument('--preview-state', help='Read-only historical JSON snapshot; never initializes a disk engine')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    engine = None if args.preview_state else Engine(args.repository, args.state_dir)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.engine = engine
    server.preview_state = args.preview_state
    logging.info('XYZBox imaging station at http://127.0.0.1:%s', args.port)
    server.serve_forever()


if __name__ == '__main__':
    main()
