import subprocess
import time
import requests
import sys

FLASK_CMD = [sys.executable, '-m', 'ARCHIVOS.app']
E2E_CMD = [sys.executable, '-m', 'pytest', 'tests/test_e2e_playwright.py', '-v']
BASE_URL = 'http://127.0.0.1:5001/auth/login'

# Inicia el servidor Flask en segundo plano
flask_proc = subprocess.Popen(FLASK_CMD)

# Espera a que el servidor esté disponible
for _ in range(30):
    try:
        r = requests.get(BASE_URL)
        if r.status_code == 200 or r.status_code == 302:
            print('✅ Flask server is up!')
            break
    except Exception:
        pass
    time.sleep(1)
else:
    print('❌ Flask server did not start in time.')
    flask_proc.terminate()
    sys.exit(1)

# Ejecuta el test E2E
result = subprocess.run(E2E_CMD)

# Termina el servidor Flask
flask_proc.terminate()
flask_proc.wait()

sys.exit(result.returncode)
