"""
Contrato de datos común para TODOS los conectores de fuente.

Cualquier fuente (JobSpy, Remotive, ATS, RSS) debe devolver "dicts
crudos" con exactamente este esquema. Así transform.py, cache.py y
alerts.py NO cambian cuando se agrega una fuente nueva.
"""
from datetime import datetime


def crudo(
    categoria,
    titulo,
    empresa,
    ubicacion,
    descripcion,
    url,
    sitio_origen,
    pais_busqueda="Worldwide",
    requiere_remoto=False,
    is_remote_flag=None,
):
    """Construye un dict "crudo" estandarizado para el pipeline."""
    return {
        "categoria":       categoria,
        "pais_busqueda":   pais_busqueda,
        "requiere_remoto": requiere_remoto,
        "titulo":          str(titulo or ""),
        "empresa":         str(empresa or ""),
        "ubicacion":       str(ubicacion or ""),
        "descripcion":     str(descripcion or ""),
        "url":             str(url or "").strip(),
        "is_remote_flag":  is_remote_flag,
        "sitio_origen":    sitio_origen,
        "fecha_detectada": datetime.now().isoformat(timespec="seconds"),
    }


def es_url_valida(url):
    """Filtra registros sin URL (la URL es la clave de deduplicación)."""
    return bool(url) and url.startswith("http")
