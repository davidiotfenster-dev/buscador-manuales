# Scripts de verificación manual

Estos scripts **no son parte de la suite automática de `pytest`** (no están en `tests/`, y
`pytest.ini` fija `testpaths = tests` para que nunca se recolecten desde aquí).

Se ejecutan a mano, con la aplicación real ya arrancada (`uvicorn app.main:app`, típicamente
vía `docker-compose up`) y una base de datos con datos reales, para comprobaciones exploratorias
o de humo que no tiene sentido automatizar como regresión (dependen de contenido real de
manuales/tickets, o de todo el stack de Docker en marcha):

- `test_docker_stack.py` — smoke test end-to-end del stack completo (login, búsqueda, tickets SAT, PDF).
- `test_search_pdf.py` — verifica que una búsqueda real devuelve un PDF servible.
- `test_search_sat.py` — prueba consultas de búsqueda contra el catálogo real de documentación SAT.
- `test_security_audit.py` — batería de comprobaciones de seguridad (RBAC, path traversal, SQLi,
  SSRF, subida de archivos, cabeceras) contra un servidor vivo.

Uso: `python tools/manual_checks/<script>.py` con el servidor corriendo en `http://localhost:8000`.

Los escenarios de estos scripts que sí aportaban cobertura de regresión real y no dependían de
un servidor externo ya se han portado a tests automáticos en `tests/api/` (usando `TestClient` y
las fixtures de `tests/conftest.py`), en particular a `tests/api/test_security.py`.
