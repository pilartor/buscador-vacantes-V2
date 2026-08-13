"""
cache.py
========
Capa de ESTADO / PERSISTENCIA del pipeline.

Responsabilidad ÚNICA de este archivo:
    - Leer y escribir `vacantes_vistas.json`, que guarda las URLs ya
      notificadas en corridas anteriores (con su fecha de detección)
      para no repetirlas.
    - Aplicar RETENCION_DIAS_VISTOS: las URLs vencidas se olvidan.

Formato:
    {
      "ultima_actualizacion": "ISO",
      "total_urls": N,
      "registros": {
         "https://...": "2026-08-12T10:00:00",   # url -> fecha detectada
         ...
      }
    }

Tolera el formato legacy (lista plana de URLs) y archivos corruptos.
"""
import json
import os
from datetime import datetime, timedelta

from config import ARCHIVO_VISTOS, RETENCION_DIAS_VISTOS


def _leer_json():
    """Devuelve el dict completo del archivo (o uno vacío)."""
    if not os.path.exists(ARCHIVO_VISTOS):
        return {}
    try:
        with open(ARCHIVO_VISTOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("   [!] cache.py: archivo de vistos corrupto, se reinicia vacío")
        return {}


def _registros(data):
    """Normaliza el contenido a {url: fecha_iso}. Soporta formato legacy."""
    registros = data.get("registros", {}) if isinstance(data, dict) else {}

    # Formato legacy (v1): data era {"urls": [...]}
    if not registros and isinstance(data, dict) and "urls" in data:
        now = datetime.now().isoformat()
        registros = {u: now for u in data["urls"]}

    return registros


def cargar_vistos():
    """
    Devuelve el SET de URLs vistas dentro de la ventana de retención.
    Las URLs vencidas se ignoran (y se limpian en el próximo guardado).
    """
    data = _leer_json()
    registros = _registros(data)
    corte = datetime.now() - timedelta(days=RETENCION_DIAS_VISTOS)

    vistas = set()
    for url, fecha_str in registros.items():
        try:
            fecha = datetime.fromisoformat(fecha_str)
        except (ValueError, TypeError):
            fecha = None
        if fecha is None or fecha >= corte:
            vistas.add(url)

    return vistas


def guardar_vistos(urls_vistas):
    """
    Guarda el set de URLs actualizado. Mantiene las fechas ya conocidas
    y estampa la fecha actual para las nuevas. Limpia URLs vencidas.
    """
    data = _leer_json()
    registros = _registros(data)
    corte = datetime.now() - timedelta(days=RETENCION_DIAS_VISTOS)

    # Limpiar vencidas
    registros = {
        url: fecha for url, fecha in registros.items()
        if _dentro_ventana(fecha, corte)
    }

    now = datetime.now().isoformat(timespec="seconds")
    for url in urls_vistas:
        if url not in registros:
            registros[url] = now

    salida = {
        "ultima_actualizacion": datetime.now().isoformat(timespec="seconds"),
        "total_urls": len(registros),
        "registros": dict(sorted(registros.items())),
    }
    with open(ARCHIVO_VISTOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)


def _dentro_ventana(fecha_str, corte):
    try:
        return datetime.fromisoformat(fecha_str) >= corte
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    vistos = cargar_vistos()
    print(f"URLs vistas (ventana de {RETENCION_DIAS_VISTOS} días): {len(vistos)}")
