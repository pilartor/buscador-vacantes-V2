"""
Conector: bolsas de empleo SPA (Bumeran, ZonaJobs).

Estos portales renderizan todo el contenido con JavaScript (SPA), por lo
que no basta con urllib/requests: se usa Playwright (chromium headless).

Flujo por (sitio, término):
    1. Abrir la URL de búsqueda (/empleos-busqueda-{keyword}.html) y
       esperar a que carguen las tarjetas.
    2. Cada tarjeta es un <a href="/empleos/{slug}-{id}.html"> con un <h2>
       (título) y varios <h3> (fecha / empresa / ubicación / modalidad).
       Las tarjetas suelen incluir la descripción completa inline.
    3. Si la tarjeta no trae descripción, se abre el detalle en una page
       separada (para no destruir el contexto de la búsqueda) y se recorta
       desde "Descripción del puesto".

La URL /busquedas/empleos-de-{kw} responde 404/fallback, así que el formato
correcto es /empleos-busqueda-{kw}.html (definido en config SPA_CONFIG).

Devuelve dicts "crudos" con el contrato de sources/base.py.
"""
import re
import time

from config import (
    FUENTES_SPA,
    SPA_CONFIG,
    SPA_TERMINOS,
    SPA_MAX_POR_BUSQUEDA,
    SPA_TIMEOUT_MS,
)
from sources.base import crudo, es_url_valida


def _slug(texto):
    """minúsculas, sin acentos, espacios -> '-'."""
    texto = texto.lower().replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def _es_fecha(t):
    return bool(re.search(r"(?i)^publicado|^hace|días|día|horas|hora|minuto|segundo", t))


def _es_ubicacion(t):
    return bool(re.search(r",|capital federal|buenos aires|caba|provincia", t, re.I)) and len(t) < 60


def _es_modalidad(t):
    return bool(re.search(r"(?i)^remoto|^híbrido|^hibrido|^presencial|^mixto|^híbrida|postulación", t))


def _extraer_sitio(site, categoria, termino, page, detalle_page):
    """Extrae las vacantes de un (site, término).

    `page` se mantiene en los resultados de búsqueda; `detalle_page` se usa
    solo para abrir vacantes cuyo card no incluye descripción.
    """
    cfg = SPA_CONFIG[site]
    url = cfg["base_url"].format(slug=_slug(termino))
    dominio = re.match(r"https://([^/]+)", cfg["base_url"]).group(1)

    try:
        page.goto(url, timeout=SPA_TIMEOUT_MS + 5000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector(cfg["card"], timeout=SPA_TIMEOUT_MS)
        except Exception:
            # Sin tarjetas: si aparece el marcador de "sin resultados", salir rápido.
            try:
                page.wait_for_selector('text=No encontramos', timeout=4000)
            except Exception as e:
                print(f"   [!] [spa:{site}] carga de '{url}' -> {e}")
                return []
    except Exception as e:
        print(f"   [!] [spa:{site}] carga de '{url}' -> {e}")
        return []

    cards = page.query_selector_all(cfg["card"])
    if not cards:
        print(f"   [!] [spa:{site}] sin resultados en '{termino}'")
        return []

    crudos = []
    procesadas = 0
    i = 0

    while i < min(len(cards), SPA_MAX_POR_BUSQUEDA * 3) and procesadas < SPA_MAX_POR_BUSQUEDA:
        card = cards[i]
        try:
            link = card.get_attribute("href") or ""
        except Exception:
            # Contexto destruido por re-render de la SPA: re-consultar y reintentar.
            cards = page.query_selector_all(cfg["card"])
            if i >= len(cards):
                break
            card = cards[i]
            try:
                link = card.get_attribute("href") or ""
            except Exception:
                break

        if link.startswith("/"):
            link = f"https://{dominio}{link}"
        if not es_url_valida(link):
            i += 1
            continue

        h2 = card.query_selector("h2")
        titulo = h2.inner_text().strip() if h2 else ""
        if not titulo:
            i += 1
            continue

        h3 = [h.inner_text().strip() for h in card.query_selector_all("h3")]
        empresa = next(
            (t for t in h3 if not _es_fecha(t) and not _es_ubicacion(t) and not _es_modalidad(t) and len(t) > 1),
            "",
        )
        ubicacion = next((t for t in h3 if _es_ubicacion(t)), "")
        if not ubicacion:
            modalidad = next((t for t in h3 if _es_modalidad(t)), "")
            if modalidad.lower().startswith("remoto"):
                ubicacion = modalidad

        cuerpo = card.inner_text()
        lineas = [l.strip() for l in cuerpo.splitlines() if l.strip()]
        descripcion = " ".join(lineas[3:])[:3500]
        if len(descripcion) < 120:
            # Card sin descripción inline (ej. variante "Postulación rápida").
            descripcion = _extraer_descripcion_spa(detalle_page, link)
            time.sleep(1.5)

        crudos.append(
            crudo(
                categoria=categoria,
                titulo=titulo,
                empresa=empresa,
                ubicacion=ubicacion or "Argentina",
                descripcion=descripcion,
                url=link,
                sitio_origen=site,
                pais_busqueda="Argentina",
                is_remote_flag="remoto" in (titulo + ubicacion).lower(),
            )
        )
        procesadas += 1
        i += 1

    return crudos


def _extraer_descripcion_spa(detalle_page, link):
    """Abre el detalle en una page separada y recorta desde 'Descripción del puesto'."""
    try:
        detalle_page.goto(link, timeout=SPA_TIMEOUT_MS + 5000, wait_until="domcontentloaded")
        try:
            detalle_page.wait_for_selector("text=/descripción del puesto/i", timeout=SPA_TIMEOUT_MS)
        except Exception:
            pass
        body = detalle_page.inner_text("body")
    except Exception as e:
        print(f"   [!] [spa] detalle {link} -> {e}")
        return ""

    m = re.search(r"(?i)descripción del puesto", body)
    if m:
        body = body[m.end():]
    body = re.split(r"(?i)empleos relacionados", body)[0]
    lineas = [l.strip() for l in body.splitlines() if len(l.strip()) > 2]
    return " ".join(lineas)[:3500]


def extraer(categoria):
    """Recorre los sitios SPA configurados para la categoría."""
    terminos = SPA_TERMINOS.get(categoria, [])
    if not terminos:
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("   [!] [spa] Playwright no está instalado. "
              "pip install playwright && playwright install chromium")
        return []

    crudos = []
    vistos = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
            locale="es-AR",
        )
        detalle_page = browser.new_page(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
            locale="es-AR",
        )

        for site in FUENTES_SPA:
            if site not in SPA_CONFIG:
                continue
            print(f"   [>] [spa:{site}] para categoría {categoria}")
            for termino in terminos:
                for cr in _extraer_sitio(site, categoria, termino, page, detalle_page):
                    clave = cr["url"].split("?")[0]
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    crudos.append(cr)
                time.sleep(2)

        browser.close()

    return crudos


if __name__ == "__main__":
    import sys
    categoria = sys.argv[1] if len(sys.argv) > 1 else "ETL"
    print(f"Probando SPA para '{categoria}'...")
    resultados = extraer(categoria)
    print(f"Total extraído: {len(resultados)}")
    if resultados:
        print(resultados[0])
