"""
Conector: Computrabajo (bolsa de empleo LATAM, multi-país).

Computrabajo sirve HTML estático en sus listados y ofertas (sin
JavaScript necesario), por lo que se puede consumir con urllib puro.
Países soportados vía subdominio de 2 letras:
    ar, cl, mx, co, pe, uy, ec, bo, pa, pr, ve, gt, do, hn, sv, cr, ni

Estructura parseada (listado):
    <article class="box_offer" data-id="...">
        <h2><a class="js-o-link" href="/ofertas-de-trabajo/...">Título</a></h2>
        <p><a class="t_ellipsis" href=".../empresa...">Empresa</a></p>
        <p><span>Ubicación</span></p>
        <div>... modalidad (Presencial y remoto / Remoto / ...)</div>
        <p>Hace X horas</p>

La descripción completa se obtiene de la página de detalle de cada
oferta (se limita con COMPUTRABAJO_MAX_POR_BUSQUEDA para no saturar).

Devuelve dicts "crudos" con el contrato de sources/base.py.
"""
import re
import html as ihtml
import time
import urllib.request

from config import (
    COMPUTRABAJO_PAISES,
    COMPUTRABAJO_PAISES_POR_PLAN,
    COMPUTRABAJO_TERMINOS,
    COMPUTRABAJO_MAX_POR_BUSQUEDA,
    PAUSA_ENTRE_BUSQUEDAS,
)
from sources.base import crudo, es_url_valida

TIMEOUT_SEG = 25

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# Mapa cc -> nombre de país usado como pais_busqueda en el pipeline
PAIS_POR_CC = {
    "ar": "Argentina", "cl": "Chile", "mx": "Mexico", "co": "Colombia",
    "pe": "Peru", "uy": "Uruguay", "ec": "Ecuador", "bo": "Bolivia",
    "pa": "Panama", "pr": "Puerto Rico", "ve": "Venezuela", "gt": "Guatemala",
    "do": "Dominican Republic", "hn": "Honduras", "sv": "El Salvador",
    "cr": "Costa Rica", "ni": "Nicaragua",
}

# Los países hispanos remotos del plan IDMC comparten nombre con el mapa
PAIS_HISPANO = {
    "Chile", "Peru", "Mexico", "Colombia", "Uruguay", "Costa Rica",
    "Venezuela", "Ecuador", "Panama",
}


def _get(url):
    """GET simple con timeout y retorno de texto (o None)."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEG) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"   [!] [computrabajo] GET {url} -> {e}")
        return None


def _a_limpio(texto):
    """Texto plano sin HTML, sin acentos, minúsculas -> slug."""
    texto = ihtml.unescape(re.sub(r"<[^>]+>", " ", str(texto or "")))
    texto = texto.lower()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto


def _extraer_listado(categoria, cc, termino):
    """Trae la lista de ofertas de un (país, término) como list[dict]."""
    slug = _a_limpio(termino)
    url = f"https://{cc}.computrabajo.com/trabajo-de-{slug}"
    html = _get(url)
    if not html:
        return []

    articulos = re.split(r'<article class="box_offer', html)[1:]
    ofertas = []

    for bloque in articulos:
        # data-id -> clave única de la oferta
        m_id = re.search(r"data-id=['\"]([^'\"]+)", bloque)
        oid = m_id.group(1) if m_id else ""

        # URL + título
        m_link = re.search(r'href="(/ofertas-de-trabajo/[^"]+)"[^>]*>\s*([^<]+)', bloque)
        if not m_link:
            continue
        path = re.split(r"[#?]", m_link.group(1))[0]  # quita fragmentos #lc=...
        titulo = ihtml.unescape(m_link.group(2)).strip()
        url_oferta = f"https://{cc}.computrabajo.com{path}"
        if not es_url_valida(url_oferta):
            continue

        # Empresa
        m_emp = re.search(r'href="[^"]*\/[^"]*"[^>]*>\s*([^<]{2,60})\s*<', bloque)
        empresa = m_emp.group(1).strip() if m_emp else ""
        # La primera <a> con href absoluto hacia /empresas o la empresa
        m_emp2 = re.search(r'href="https://[^"]+/[^"]*"[^>]*>\s*([^<]{2,60})\s*<', bloque)
        if m_emp2:
            empresa = ihtml.unescape(m_emp2.group(1)).strip()

        # Ubicación: primer <span class="mr10"> o el <p class="fs16 fc_base mt5">
        m_ubi = re.search(r'<p class="fs16 fc_base mt5">\s*<span[^>]*>\s*([^<]+)', bloque)
        ubicacion = ihtml.unescape(m_ubi.group(1)).strip() if m_ubi else ""

        # Modalidad: textos en el bloque (remoto / presencial y remoto)
        texto_bloque = re.sub(r"<[^>]+>", " ", bloque).lower()
        modalidad = "presencial"
        if "remoto" in texto_bloque:
            modalidad = "remoto" if "presencial y remoto" not in texto_bloque and "hibrido" not in texto_bloque else "hibrido"
        if "híbrido" in texto_bloque or "hibrido" in texto_bloque or "mixto" in texto_bloque:
            modalidad = "hibrido"

        # Salario (opcional)
        m_sal = re.search(r"\$\s?[\d\.,]+", texto_bloque)
        salario = m_sal.group(0) if m_sal else ""

        # Fecha relativa
        m_fecha = re.search(r"(hace\s+\d+\s+\w+|ayer)", texto_bloque)

        ofertas.append({
            "id": oid,
            "titulo": titulo,
            "empresa": empresa,
            "ubicacion": ubicacion,
            "modalidad": modalidad,
            "salario": salario,
            "fecha": m_fecha.group(1) if m_fecha else "",
            "url": url_oferta,
        })

    return ofertas


_NAV_TOKENS = (
    "buscar postulaciones", "avisos favoritos", "crear cv", "ingresar",
    "menú", "login", "buscar empresas", "recruiters", "salarios",
    "consejos para encontrar", "crear alerta", "mi ubicación",
)

def _es_texto_descripcion(texto):
    """True si el párrafo parece contenido real de la oferta (no menú)."""
    if len(texto) < 100:
        return False
    bajo = texto.lower()
    return not any(t in bajo for t in _NAV_TOKENS)


def _extraer_descripcion(url_oferta):
    """Devuelve la descripción de texto de una oferta (o '' si falla)."""
    html = _get(url_oferta)
    if not html:
        return ""

    parrafos = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)
    piezas = []
    for p in parrafos:
        texto = ihtml.unescape(re.sub(r"<[^>]+>", " ", p))
        texto = re.sub(r"\s+", " ", texto).strip()
        if _es_texto_descripcion(texto):
            piezas.append(texto)

    # Si no hubo párrafos largos, cae en divs con la clase de descripción
    if not piezas:
        m = re.search(r'<div[^>]*class="[^"]*(descripcion|description|descriptionJob)[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if m:
            texto = ihtml.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
            texto = re.sub(r"\s+", " ", texto).strip()
            if _es_texto_descripcion(texto):
                piezas.append(texto)

    return " ".join(piezas)


def extraer(categoria):
    """
    Recorre (país, término) de la categoría y devuelve crudos.
    Se conserva el primer crudo por id (evita duplicados entre países).
    """
    terminos = COMPUTRABAJO_TERMINOS.get(categoria, [])
    if not terminos:
        return []

    crudos = []
    vistos_ids = set()
    # Plan A = todos los países; B/C/D = solo Argentina (ver config).
    paises_plan = COMPUTRABAJO_PAISES_POR_PLAN.get(categoria, COMPUTRABAJO_PAISES)
    paises = [c for c in paises_plan if c in PAIS_POR_CC]

    for cc in paises:
        pais_nombre = PAIS_POR_CC[cc]
        for termino in terminos:
            ofertas = _extraer_listado(categoria, cc, termino)
            print(f"   [>] [computrabajo:{cc}] '{termino}' -> {len(ofertas)} ofertas")
            procesadas = 0

            for of in ofertas:
                if not of["id"] or of["id"] in vistos_ids:
                    continue
                if procesadas >= COMPUTRABAJO_MAX_POR_BUSQUEDA:
                    break

                vistos_ids.add(of["id"])
                procesadas += 1

                descripcion = _extraer_descripcion(of["url"])
                if len(descripcion) < 80:
                    continue  # sin descripción no se puede evaluar el rol

                requiere_remoto = pais_nombre not in PAIS_HISPANO
                crudos.append(
                    crudo(
                        categoria=categoria,
                        titulo=of["titulo"],
                        empresa=of["empresa"],
                        ubicacion=f"{of['ubicacion']} ({pais_nombre})",
                        descripcion=descripcion,
                        url=of["url"],
                        sitio_origen=f"computrabajo:{cc}",
                        pais_busqueda=pais_nombre,
                        requiere_remoto=requiere_remoto,
                        is_remote_flag=of["modalidad"] == "remoto",
                    )
                )
                time.sleep(PAUSA_ENTRE_BUSQUEDAS)

        time.sleep(PAUSA_ENTRE_BUSQUEDAS)

    return crudos


if __name__ == "__main__":
    import sys
    categoria = sys.argv[1] if len(sys.argv) > 1 else "ETL"
    print(f"Probando Computrabajo para '{categoria}'...")
    resultados = extraer(categoria)
    print(f"Total extraído: {len(resultados)}")
    if resultados:
        print(resultados[0])
