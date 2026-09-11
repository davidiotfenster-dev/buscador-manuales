import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"

def request_json(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(resp_body.decode("utf-8")), resp_body
            return resp.status, None, resp_body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return e.code, err_body, err_body

def login(email, password):
    url = f"{BASE_URL}/api/token"
    form_data = urllib.parse.urlencode({"username": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=form_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["access_token"]

def test_flujo_sat_auto_email():
    print("1. Iniciando sesión como administrador...")
    token = login("admin@empresa.com", "admin123")
    print("   -> Sesión iniciada correctamente. Token obtenido.")

    print("\n2. Probando endpoint POST /api/sat/tickets/auto-registrar-enviar...")
    payload_auto = {
        "instalador": "Carlos Ruiz (Climalit Instalaciones)",
        "email": "carlos.ruiz@ejemplo-instalador.es",
        "telefono": "678 12 34 56",
        "obra": "Residencial Gran Vía - Bloque B",
        "distribuidor": "IoT Fenster / MySmartWindow",
        "dispositivo": "Connect-1",
        "motor": "Somfy 4 hilos mecánico 10Nm",
        "sintoma": "La persiana sube al pulsar la orden de bajar en la App",
        "diagnostico": "Inversión de fases de maniobra (Marrón por Negro en bornera)",
        "solucion": "1. Desconectar el magnetotérmico de 10A.\n2. Intercambiar los cables marrón y negro en las bornes de salida.\n3. O pulsar 'Invertir Sentido de Giro' en la App.",
        "estado": "resuelto",
        "prioridad": "normal",
        "notas": "Resolución técnica automática enviada por correo al técnico.",
        "enviar_email": True,
        "manual_info": {
            "nombre": "Problemas_y_Soluciones_SAT.pdf",
            "pagina": 1
        }
    }

    status, data_auto, _ = request_json("POST", "/api/sat/tickets/auto-registrar-enviar", payload_auto, token=token)
    assert status == 201, f"Error auto-registrar: {status} - {data_auto}"
    print("   -> Respuesta recibida:")
    print("      ok:", data_auto.get("ok"))
    ticket = data_auto.get("ticket", {})
    ticket_id = ticket.get("id")
    numero_ticket = ticket.get("numero_ticket")
    print(f"      Ticket ID: {ticket_id} (#{numero_ticket})")
    print(f"      Instalador: {ticket.get('instalador')}")
    print(f"      Email: {ticket.get('email')}")
    print(f"      PDF URL: {data_auto.get('pdf_url')}")
    
    email_res = data_auto.get("email_resultado", {})
    print("      Email Resultado:", email_res)
    assert email_res.get("enviado") is True, (
        f"Error en envio de correo: {email_res}. "
        "Requiere SMTP_HOST, SMTP_USER y SMTP_PASSWORD configurados: sin ellos el modo simulado devuelve enviado=False."
    )
    assert email_res.get("destinatario") == "carlos.ruiz@ejemplo-instalador.es"

    print("\n3. Verificando descarga y formato binario del PDF generado...")
    pdf_url = data_auto.get("pdf_url")
    status, _, pdf_bytes = request_json("GET", pdf_url, token=token)
    assert status == 200, f"Error al obtener PDF: {status}"
    assert pdf_bytes.startswith(b"%PDF"), "El archivo devuelto no tiene la cabecera estándar de PDF"
    print(f"   -> PDF generado y validado con éxito. Tamaño: {len(pdf_bytes)} bytes.")

    print("\n4. Probando reenvío manual de correo POST /api/sat/tickets/{id}/enviar-email...")
    status, data_reenvio, _ = request_json(
        "POST",
        f"/api/sat/tickets/{ticket_id}/enviar-email",
        {"email": "supervisor.sat@iotfenster.com"},
        token=token
    )
    assert status == 200, f"Error en reenvío: {data_reenvio}"
    print("   -> Reenvío exitoso:", data_reenvio)
    assert data_reenvio.get("ok") is True

    print("\n5. Verificando presencia en la lista general de tickets CRM...")
    status, tickets, _ = request_json("GET", "/api/sat/tickets", token=token)
    assert status == 200
    encontrado = next((t for t in tickets if t["id"] == ticket_id), None)
    assert encontrado is not None, "El ticket recién creado no aparece en el listado CRM"
    assert encontrado["email"] in ("supervisor.sat@iotfenster.com", "carlos.ruiz@ejemplo-instalador.es")
    print(f"   -> Ticket #{numero_ticket} verificado en listado CRM con email: {encontrado['email']}")

    print("\n[OK] TODAS LAS PRUEBAS DEL FLUJO AUTOMATICO SAT PASARON EXITOSAMENTE!")

if __name__ == "__main__":
    test_flujo_sat_auto_email()
