import requests

BASE_URL = "http://localhost:8000"

# 1. Login as admin
resp_login = requests.post(f"{BASE_URL}/api/token", data={"username": "admin@empresa.com", "password": "admin123"})
assert resp_login.status_code == 200, f"Login failed: {resp_login.text}"
token = resp_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Search for 'c-pulsar'
resp_search = requests.get(f"{BASE_URL}/api/buscar?q=c-pulsar", headers=headers)
assert resp_search.status_code == 200, f"Search failed: {resp_search.text}"
data = resp_search.json()

manuales = data.get("manuales", [])
print(f"Manuales encontrados: {len(manuales)}")
assert len(manuales) > 0, "No se encontraron manuales para 'c-pulsar'"

primero = manuales[0]
print(f"Manual 1: nombre={primero.get('nombre')}")
print(f"Manual 1: archivo={primero.get('archivo')}")
print(f"Manual 1: nombre_archivo={primero.get('nombre_archivo')}")
print(f"Manual 1: pagina_encontrada={primero.get('pagina_encontrada')}")

assert primero.get("archivo"), "El campo 'archivo' está vacío o es None!"
assert primero.get("archivo") != "undefined", "El campo 'archivo' es el string 'undefined'!"

# 3. Request the actual PDF file using the 'archivo' parameter
pdf_filename = primero.get("archivo")
pdf_url = f"{BASE_URL}/manuales/{pdf_filename}?token={token}"
resp_pdf = requests.get(pdf_url)
print(f"Respuesta PDF URL {pdf_url} -> Status Code: {resp_pdf.status_code}")
print(f"Content-Type: {resp_pdf.headers.get('content-type')}")
assert resp_pdf.status_code == 200, f"Error descargando PDF: {resp_pdf.status_code}"
assert "application/pdf" in resp_pdf.headers.get("content-type", ""), "No es application/pdf"
print("TODO CORRECTO: El PDF se resuelve y sirve perfectamente (HTTP 200 application/pdf).")
