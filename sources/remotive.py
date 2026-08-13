"""
Conector: Remotive (tablón de empleo remoto).

Usa la API pública y gratuita de Remotive (sin key):
    GET https://remotive.com/api/remote-jobs?search={query}

Devuelve dicts "crudos" con el contrato de sources/base.py.
Es una fuente de bajo riesgo (API pública, términos y condiciones
diseñados para lectura programática).
"""
from config import REMOTIVE_BASE_URL
from sources.base import crudo, es_url_valida

TIMEOUT_SEG = 30


def extraer(query, categoria):
    """Busca vacantes remotas que coincidan con `query` y devuelve crudos."""
    import requests  # import perezoso: no bloquea módulos sin la dependencia

    try:
        resp = requests.get(
            REMOTIVE_BASE_URL,
            params={"search": query},
            timeout=TIMEOUT_SEG,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"   [!] [remotive] Error: {e}")
        return []

    crudos = []
    for job in data.get("jobs", []) or []:
        url = str(job.get("url", "") or "").strip()
        if not es_url_valida(url):
            continue
        crudos.append(
            crudo(
                categoria=categoria,
                titulo=job.get("title", ""),
                empresa=job.get("company_name", ""),
                ubicacion=job.get("candidate_required_location", "Worldwide"),
                descripcion=job.get("description", ""),
                url=url,
                sitio_origen="remotive",
                pais_busqueda="Worldwide",
                is_remote_flag=True,  # Remotive = remoto por definición
            )
        )
    return crudos
