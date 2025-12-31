from wsgiref.simple_server import make_server
import os
import sys

# Ensure project root is on PYTHONPATH
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from wsgi import application

if __name__ == '__main__':
    port = int(os.environ.get('WsgiTestPort', '8000'))
    print(f"Starting WSGI test server on http://127.0.0.1:{port}")
    httpd = make_server('127.0.0.1', port, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Stopping WSGI test server')
        httpd.server_close()
