"""Qué contesta el envío del parte SAT cuando no hay SMTP, y cuando lo hay.

Este módulo ya mintió una vez: sin SMTP configurado devolvía `enviado: True`,
así que el técnico cerraba la llamada convencido de que el parte había salido
cuando solo se había escrito una línea de log. Se corrigió en la Fase 0, y
estos tests existen para que no vuelva.

El otro fallo era más callado todavía: las variables SMTP se leen del entorno
del proceso, y `docker-compose.yml` no las pasaba al contenedor. Rellenar el
`.env` no cambiaba nada y el parte seguía sin salir, sin que nada lo delatara.
Eso se arregla en el compose, que no se puede probar aquí; lo que sí se prueba
es que en cuanto las tres variables tienen valor, se intenta el envío de
verdad.
"""

from unittest.mock import MagicMock

import pytest

from app import email_sender


class _Ticket:
    numero_ticket = "SAT-2026-0001"
    dispositivo = "Konect Elite"
    email = "instalador@ejemplo.com"
    sintoma = "No vincula"
    diagnostico = ""
    solucion = ""
    instalador = "Instalador de prueba"
    obra = ""
    estado = "resuelto"


@pytest.fixture
def sin_smtp(monkeypatch):
    for var in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.setattr(email_sender, var, "")


@pytest.fixture
def con_smtp(monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.ejemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "soporte@ejemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "clave-de-aplicacion")


def test_sin_smtp_no_dice_que_lo_ha_enviado(sin_smtp):
    """La regresión que importa: `enviado` no puede ser True si no salió."""
    res = email_sender.enviar_email_resolucion_sat(_Ticket(), pdf_bytes=b"%PDF-1.4")

    assert res["enviado"] is False
    assert res["modo"] == "simulado"


def test_sin_smtp_explica_por_que(sin_smtp):
    """Quien lo lea tiene que entender que falta configurar SMTP, no que el
    correo del cliente esté mal: son dos arreglos distintos."""
    res = email_sender.enviar_email_resolucion_sat(_Ticket(), pdf_bytes=b"%PDF-1.4")

    assert "SMTP" in res["mensaje"]
    assert "NO enviado" in res["mensaje"]


def test_sin_destinatario_no_se_intenta_nada(con_smtp):
    ticket = _Ticket()
    ticket.email = ""

    res = email_sender.enviar_email_resolucion_sat(ticket, pdf_bytes=b"%PDF-1.4")

    assert res["enviado"] is False
    assert "correo electrónico de destino" in res["motivo"]


def test_con_las_tres_variables_se_envia_de_verdad(con_smtp, monkeypatch):
    """Que estén puestas en el entorno es justo lo que el compose no hacía
    llegar al contenedor."""
    servidor = MagicMock()
    smtp = MagicMock()
    smtp.return_value.__enter__.return_value = servidor
    monkeypatch.setattr(email_sender.smtplib, "SMTP", smtp)

    res = email_sender.enviar_email_resolucion_sat(_Ticket(), pdf_bytes=b"%PDF-1.4")

    assert res["enviado"] is True
    assert res["modo"] == "smtp_real"
    servidor.login.assert_called_once()
    destinatarios = servidor.sendmail.call_args[0][1]
    assert destinatarios == ["instalador@ejemplo.com"]


def test_si_el_servidor_falla_no_se_da_por_enviado(con_smtp, monkeypatch):
    monkeypatch.setattr(
        email_sender.smtplib, "SMTP",
        MagicMock(side_effect=OSError("connection refused")),
    )

    res = email_sender.enviar_email_resolucion_sat(_Ticket(), pdf_bytes=b"%PDF-1.4")

    assert res["enviado"] is False
    assert res["modo"] == "smtp_error"
    assert "connection refused" in res["error"]


def test_el_pdf_viaja_adjunto(con_smtp, monkeypatch):
    servidor = MagicMock()
    smtp = MagicMock()
    smtp.return_value.__enter__.return_value = servidor
    monkeypatch.setattr(email_sender.smtplib, "SMTP", smtp)

    email_sender.enviar_email_resolucion_sat(_Ticket(), pdf_bytes=b"%PDF-1.4 contenido")

    mensaje = servidor.sendmail.call_args[0][2]
    assert "Parte_SAT_SAT-2026-0001.pdf" in mensaje
