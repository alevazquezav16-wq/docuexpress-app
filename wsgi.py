# wsgi.py para PythonAnywhere

from ARCHIVOS.app import create_app

app = create_app()
application = app
