"""
Conector: ATS de empresas objetivo.

Muchas empresas publican sus vacantes a través de ATS con APIs públicas
de lectura (sin autenticación). Cada plataforma se implementa como una
función _extraer_* y se recorre con la lista de empresas de config.py.

Endpoints públicos soportados:
    Workable:         GET https://apply.workable.com/api/v1/widget/companies/{slug}
    Lever:            GET https://api.lever.co/v0/postings/{slug}?mode=json
    Greenhouse:       GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
    SmartRecruiters:  GET https://api.smartrecruiters.com/v1/companies/{slug}/postings
"""
import re
import time
from html import unescape

import requests

from config import (
    ATS_WORKABLE,
    ATS_LEVER,
    ATS_GREENHOUSE,
    ATS_SMARTRECRUITERS,
    ATS_DETALLE_DESCRIPCION,
    PAUSA_ENTRE_BUSQUEDAS,
)
from sources.base import crudo, es_url_valida

TIMEOUT_SEG = 30


def _texto_html(html):
    """Convierte HTML de descripción a texto plano legible."""
    texto = re.sub(r"<[^>]+>", " ", str(html or ""))
    return re.sub(r"\s+", " ", unescape(texto)).strip()


def _extraer_workable(categoria):
    import requests

    crudos = []
    for slug in ATS_WORKABLE:
        url = f"https://apply.workable.com/api/v1/widget/companies/{slug}"
        try:
            data = requests.get(url, timeout=TIMEOUT_SEG).json()
        except Exception as e:
            print(f"   [!] [workable:{slug}] Error: {e}")
            continue

        for job in data.get("jobs", []) or []:
            link = str(job.get("url", "") or "").strip()
            if not es_url_valida(link):
                continue
            pais = job.get("country", "") or job.get("city", "") or "Worldwide"
            crudos.append(
                crudo(
                    categoria=categoria,
                    titulo=job.get("title", ""),
                    empresa=job.get("company_name", slug),
                    ubicacion=pais,
                    descripcion=job.get("description", ""),
                    url=link,
                    sitio_origen="workable",
                    pais_busqueda="Worldwide",
                )
            )
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return crudos


def _extraer_lever(categoria):
    import requests

    crudos = []
    for slug in ATS_LEVER:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            data = requests.get(url, timeout=TIMEOUT_SEG).json()
        except Exception as e:
            print(f"   [!] [lever:{slug}] Error: {e}")
            continue

        for job in data or []:
            link = str(job.get("hostedUrl", "") or "").strip()
            if not es_url_valida(link):
                continue
            ubicacion = ", ".join(job.get("categories", {}).get("allLocations", []) or []) or "Worldwide"
            crudos.append(
                crudo(
                    categoria=categoria,
                    titulo=job.get("text", ""),
                    empresa=job.get("company", slug),
                    ubicacion=ubicacion,
                    descripcion=job.get("descriptionPlain", "") or job.get("description", ""),
                    url=link,
                    sitio_origen="lever",
                    pais_busqueda="Worldwide",
                )
            )
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return crudos


def _extraer_greenhouse(categoria):
    """GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs (público)."""
    crudos = []
    for slug in ATS_GREENHOUSE:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            data = requests.get(url, timeout=TIMEOUT_SEG).json()
        except Exception as e:
            print(f"   [!] [greenhouse:{slug}] Error: {e}")
            continue

        if isinstance(data, dict) and "jobs" in data:
            jobs = data["jobs"]
        elif isinstance(data, list):
            jobs = data
        else:
            jobs = []

        for job in jobs:
            link = str(job.get("absolute_url", "") or "").strip()
            if not es_url_valida(link):
                continue
            loc = (job.get("location", {}) or {}).get("name", "") or "Worldwide"
            crudos.append(
                crudo(
                    categoria=categoria,
                    titulo=job.get("title", ""),
                    empresa=job.get("company_name", slug),
                    ubicacion=loc,
                    descripcion=_texto_html(job.get("content", "")),
                    url=link,
                    sitio_origen="greenhouse",
                    pais_busqueda="Worldwide",
                )
            )
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return crudos


def _extraer_smartrecruiters(categoria):
    """
    GET https://api.smartrecruiters.com/v1/companies/{slug}/postings
    La descripción completa está en el endpoint de detalle de cada aviso.
    """
    crudos = []
    for slug in ATS_SMARTRECRUITERS:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        try:
            data = requests.get(url, timeout=TIMEOUT_SEG).json()
        except Exception as e:
            print(f"   [!] [smartrecruiters:{slug}] Error: {e}")
            continue

        for posting in data.get("content", []) or []:
            link = str(posting.get("postingUrl", "") or "").strip()
            if not es_url_valida(link):
                link = f"https://jobs.smartrecruiters.com/{slug}/{posting.get('id', '')}"
            if not es_url_valida(link):
                continue

            loc = (posting.get("location", {}) or {})
            ubicacion = loc.get("fullLocation") or loc.get("city") or "Worldwide"

            descripcion = ""
            if ATS_DETALLE_DESCRIPCION:
                pid = posting.get("id")
                if pid:
                    det_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{pid}"
                    try:
                        detalle = requests.get(det_url, timeout=TIMEOUT_SEG).json()
                        secciones = (detalle.get("jobAd", {}) or {}).get("sections", {}) or {}
                        descripcion = _texto_html(
                            (secciones.get("jobDescription", {}) or {}).get("text", "")
                        )
                    except Exception as e:
                        print(f"   [!] [smartrecruiters:{slug}] detalle {pid}: {e}")

            crudos.append(
                crudo(
                    categoria=categoria,
                    titulo=posting.get("name", ""),
                    empresa=posting.get("company", {}).get("name", slug),
                    ubicacion=ubicacion,
                    descripcion=descripcion,
                    url=link,
                    sitio_origen="smartrecruiters",
                    pais_busqueda="Worldwide",
                )
            )
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return crudos


def extraer(categoria):
    """Recorre los ATS configurados y devuelve crudos."""
    crudos = []
    crudos.extend(_extraer_workable(categoria))
    crudos.extend(_extraer_lever(categoria))
    crudos.extend(_extraer_greenhouse(categoria))
    crudos.extend(_extraer_smartrecruiters(categoria))
    return crudos
