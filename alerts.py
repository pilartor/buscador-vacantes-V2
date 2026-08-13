"""
alerts.py
=========
Capa LOAD del pipeline (notificación).

Responsabilidad ÚNICA de este archivo:
    - Construir el contenido (HTML) de las alertas.
    - Enviarlas por el canal configurado: "email" (Gmail SMTP) o
      "consola" (para probar sin configuración).

El canal es intercambiable: agregar Slack/Telegram implica un nuevo
enviador, sin tocar el resto del pipeline.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_REMITENTE,
    EMAIL_DESTINATARIO,
    EMAIL_APP_PASSWORD,
    EMAIL_ASUNTO,
    NOTIFICACION_CANAL,
)

_TAG_MODALIDAD = {
    "remoto": "🌍 Remoto",
    "hibrido": "🔄 Híbrido",
    "presencial": "🏢 Presencial",
}


# ─────────────────────────────────────────────
#  CONSTRUCCIÓN DE CONTENIDO
# ─────────────────────────────────────────────
def _fila_vacante(vacante):
    modalidad = _TAG_MODALIDAD.get(vacante.get("modalidad", ""), "—")
    return f"""
        <tr>
            <td style="padding:6px; border:1px solid #ddd; font-weight:bold;">{vacante['plan']}</td>
            <td style="padding:6px; border:1px solid #ddd;">
                <a href="{vacante['url']}">{vacante['titulo']}</a>
            </td>
            <td style="padding:6px; border:1px solid #ddd;">{vacante['empresa']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{vacante['ubicacion']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{modalidad}</td>
            <td style="padding:6px; border:1px solid #ddd;">{vacante['categoria']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{vacante['terminos_match']}</td>
        </tr>"""


def construir_html(calificadas):
    """
    Recibe lista de dicts "calificadas" y devuelve el HTML del email.
    """
    if not calificadas:
        return "<p>No se encontraron vacantes NUEVAS en esta corrida.</p>"

    filas_html = "".join(_fila_vacante(v) for v in calificadas)

    total_a = sum(1 for v in calificadas if v["plan"] == "A")
    total_b = sum(1 for v in calificadas if v["plan"] == "B")
    total_c = sum(1 for v in calificadas if v["plan"] == "C")
    total_d = sum(1 for v in calificadas if v["plan"] == "D")

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Vacantes NUEVAS encontradas</h2>
        <p>Total: {len(calificadas)} vacantes nuevas
        (Plan A: {total_a}, Plan B: {total_b}, Plan C: {total_c}, Plan D: {total_d})</p>
        <table style="border-collapse: collapse; width: 100%; font-size: 13px;">
            <thead>
                <tr style="background-color:#1F4E79; color:white;">
                    <th style="padding:6px; border:1px solid #ddd;">Plan</th>
                    <th style="padding:6px; border:1px solid #ddd;">Título</th>
                    <th style="padding:6px; border:1px solid #ddd;">Empresa</th>
                    <th style="padding:6px; border:1px solid #ddd;">Ubicación</th>
                    <th style="padding:6px; border:1px solid #ddd;">Modalidad</th>
                    <th style="padding:6px; border:1px solid #ddd;">Categoría</th>
                    <th style="padding:6px; border:1px solid #ddd;">Coincidencias</th>
                </tr>
            </thead>
            <tbody>
                {filas_html}
            </tbody>
        </table>
    </body>
    </html>
    """


def construir_html_rechazadas(rechazadas):
    """
    Recibe lista de dicts "casi califican" (Argentina) y devuelve su HTML.
    """
    if not rechazadas:
        return "<p>No hubo vacantes 'casi calificadas' NUEVAS en Argentina en esta corrida.</p>"

    filas_html = ""
    for v in rechazadas:
        filas_html += f"""
        <tr>
            <td style="padding:6px; border:1px solid #ddd; font-weight:bold;">{v['plan']}</td>
            <td style="padding:6px; border:1px solid #ddd;">
                <a href="{v['url']}">{v['titulo']}</a>
            </td>
            <td style="padding:6px; border:1px solid #ddd;">{v['empresa']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{v['ubicacion']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{v['categoria']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{v['coincidencias']}</td>
            <td style="padding:6px; border:1px solid #ddd;">{v['terminos_match']}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Vacantes rechazadas NUEVAS - Argentina (casi califican)</h2>
        <p>Total: {len(rechazadas)} vacantes con al menos 1 coincidencia pero por debajo del mínimo.</p>
        <table style="border-collapse: collapse; width: 100%; font-size: 13px;">
            <thead>
                <tr style="background-color:#A04040; color:white;">
                    <th style="padding:6px; border:1px solid #ddd;">Plan</th>
                    <th style="padding:6px; border:1px solid #ddd;">Título</th>
                    <th style="padding:6px; border:1px solid #ddd;">Empresa</th>
                    <th style="padding:6px; border:1px solid #ddd;">Ubicación</th>
                    <th style="padding:6px; border:1px solid #ddd;">Categoría</th>
                    <th style="padding:6px; border:1px solid #ddd;">Matches</th>
                    <th style="padding:6px; border:1px solid #ddd;">Términos</th>
                </tr>
            </thead>
            <tbody>
                {filas_html}
            </tbody>
        </table>
    </body>
    </html>
    """


# ─────────────────────────────────────────────
#  ENVIADORES
# ─────────────────────────────────────────────
def enviar_email(html_content, total_vacantes, asunto_base=None):
    """Envía un email HTML por Gmail (SMTP)."""
    asunto_base = asunto_base or EMAIL_ASUNTO
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{asunto_base} ({total_vacantes})"
    msg["From"] = EMAIL_REMITENTE
    msg["To"] = EMAIL_DESTINATARIO
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_REMITENTE, EMAIL_DESTINATARIO, msg.as_string())
        print(f"  [EMAIL] Email '{asunto_base}' enviado a {EMAIL_DESTINATARIO}")
    except Exception as e:
        print(f"  [!] Error enviando email '{asunto_base}': {e}")


def enviar_consola(html_content, total_vacantes, asunto_base=None):
    """Resumen en consola en texto plano (para pruebas sin Gmail)."""
    import re

    asunto_base = asunto_base or EMAIL_ASUNTO
    print(f"\n  [CONSOLA] {asunto_base} ({total_vacantes})")

    if "No se encontraron" in html_content or "No hubo" in html_content:
        print("     (sin resultados)")
        return

    # Extraer (url, titulo) de los <a href="...">Titulo</a> del HTML
    filas = re.findall(r'<a href="([^"]+)">([^<]+)</a>', html_content)
    for url, titulo in filas:
        print(f"     - {titulo}")
        print(f"       {url}")
    print()


# ─────────────────────────────────────────────
def notificar(html_content, total_vacantes, asunto_base=None):
    """
    Despacha por el canal configurado en NOTIFICACION_CANAL.
    canal="email" -> Gmail | "consola" -> prints
    """
    if NOTIFICACION_CANAL == "consola":
        enviar_consola(html_content, total_vacantes, asunto_base)
    else:
        enviar_email(html_content, total_vacantes, asunto_base)


if __name__ == "__main__":
    ejemplo = [
        {
            "plan": "A", "titulo": "Data Engineer - Snowflake", "empresa": "Empresa X",
            "ubicacion": "Buenos Aires, Argentina", "modalidad": "hibrido",
            "categoria": "ETL", "terminos_match": "Data Engineer, Snowflake",
            "url": "https://www.linkedin.com/jobs/view/EJEMPLO",
        }
    ]
    html = construir_html(ejemplo)
    notificar(html, len(ejemplo))
