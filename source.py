"""
source.py
=========
Capa EXTRACT del pipeline (fachada de fuentes).

Responsabilidad ÚNICA de este archivo:
    - Reunir vacantes "crudas" de todas las fuentes configuradas:
        * Fuentes primarias: LinkedIn + Indeed (JobSpy)
        * Fuentes secundarias: Remotive, ATS (Workable/Lever), RSS
    - NO filtra por relevancia, NO detecta idioma, NO clasifica.
      Todo eso es trabajo de transform.py.

Todas las fuentes devuelven dicts con el MISMO contrato
(sources/base.py), por lo que agregar una fuente no modifica el resto
del pipeline.
"""
import time

from config import (
    TERMINOS,
    PLANES_PAISES,
    CANTIDAD_POR_BUSQUEDA,
    HORAS_ANTIGUEDAD,
    SITIOS_BUSQUEDA,
    FUENTES_SECUNDARIAS,
    SECUNDARIAS_MAX_TERMINOS,
    PAUSA_ENTRE_BUSQUEDAS,
)
from sources.base import crudo, es_url_valida


# ─────────────────────────────────────────────
def build_or_query(terminos):
    """
    Recibe una lista de términos y arma una búsqueda OR, ej:
        ["a", "b", "c"] -> '"a" OR "b" OR "c"'
    """
    return " OR ".join(f'"{t}"' for t in terminos)


# ─────────────────────────────────────────────
#  FUENTES PRIMARIAS (JobSpy: LinkedIn + Indeed)
# ─────────────────────────────────────────────
def extraer_jobs_pais(query, pais, requiere_remoto):
    """
    Hace UNA llamada a scrape_jobs() para un país puntual.
    Devuelve el DataFrame de JobSpy, o None si hubo error / sin resultados.
    """
    from jobspy import scrape_jobs  # import perezoso

    try:
        jobs = scrape_jobs(
            site_name=SITIOS_BUSQUEDA,
            search_term=query,
            location=pais,
            is_remote=requiere_remoto,
            results_wanted=CANTIDAD_POR_BUSQUEDA,
            hours_old=HORAS_ANTIGUEDAD,
            country_indeed=pais,
            linkedin_fetch_description=True,
        )
    except Exception as e:
        print(f"   [!] Error: {e}")
        return None

    if jobs is None or len(jobs) == 0:
        print("   (sin resultados)")
        return None

    return jobs


def extraer_jobspy_categoria(categoria):
    """
    Recorre todos los (pais, requiere_remoto) de la categoría usando JobSpy.
    Devuelve lista de dicts "crudos".
    """
    query = build_or_query(TERMINOS[categoria])
    resultados = []

    for pais, requiere_remoto in PLANES_PAISES[categoria]:
        jobs = extraer_jobs_pais(query, pais, requiere_remoto)
        if jobs is None:
            continue

        for _, job in jobs.iterrows():
            url = str(job.get('job_url', '') or '').strip()
            if not es_url_valida(url):
                continue
            resultados.append(
                crudo(
                    categoria=categoria,
                    titulo=job.get('title', ''),
                    empresa=job.get('company', ''),
                    ubicacion=job.get('location', ''),
                    descripcion=job.get('description', ''),
                    url=url,
                    sitio_origen=str(job.get('site', '') or ''),
                    pais_busqueda=pais,
                    requiere_remoto=requiere_remoto,
                    is_remote_flag=job.get('is_remote', None),
                )
            )

        time.sleep(PAUSA_ENTRE_BUSQUEDAS)

    return resultados


# ─────────────────────────────────────────────
#  FUENTES SECUNDARIAS (bajo riesgo)
# ─────────────────────────────────────────────
def extraer_secundarias_categoria(categoria):
    """
    Ejecuta los conectores secundarios configurados (remotive/ats/rss)
    usando los primeros términos de la categoría como query.
    Devuelve lista de dicts "crudos".
    """
    terminos = TERMINOS[categoria][:SECUNDARIAS_MAX_TERMINOS]
    query = " ".join(terminos)

    crudos = []

    if "remotive" in FUENTES_SECUNDARIAS:
        from sources.remotive import extraer as extraer_remotive

        print(f"   [>] Fuente secundaria: remotive")
        crudos.extend(extraer_remotive(query, categoria))

    if "computrabajo" in FUENTES_SECUNDARIAS:
        from sources.computrabajo import extraer as extraer_computrabajo

        print(f"   [>] Fuente secundaria: computrabajo")
        crudos.extend(extraer_computrabajo(categoria))

    if "ats" in FUENTES_SECUNDARIAS:
        from sources.ats import extraer as extraer_ats

        print(f"   [>] Fuente secundaria: ats")
        crudos.extend(extraer_ats(categoria))

    if "rss" in FUENTES_SECUNDARIAS:
        from sources.rss import extraer as extraer_rss

        print(f"   [>] Fuente secundaria: rss")
        crudos.extend(extraer_rss(categoria))

    if "spa" in FUENTES_SECUNDARIAS:
        from sources.spa import extraer as extraer_spa

        print(f"   [>] Fuente secundaria: spa")
        crudos.extend(extraer_spa(categoria))

    return crudos


# ─────────────────────────────────────────────
def extraer_jobs_categoria(categoria):
    """
    Función principal de este módulo: devuelve TODOS los crudos de una
    categoría (fuentes primarias + secundarias), sin filtrar nada.
    """
    crudos = extraer_jobspy_categoria(categoria)
    crudos.extend(extraer_secundarias_categoria(categoria))
    return crudos


# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    categoria = sys.argv[1] if len(sys.argv) > 1 else "ETL"
    print(f"Probando extracción para categoría '{categoria}'...")
    resultados = extraer_jobs_categoria(categoria)
    print(f"Total extraído: {len(resultados)}")
    if resultados:
        print(resultados[0])
