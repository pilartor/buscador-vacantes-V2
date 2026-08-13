"""
logging_config.py
=================
Configuración del logging del proyecto (auditoría de corridas).

Escribe en consola Y en un archivo persistente (Data/corridas.log)
para auditoría posterior (RF-40 del documento de especificaciones).
"""
import logging
import os
import sys

from config import ARCHIVO_LOG


def setup_logging(nivel=logging.INFO):
    # Consolas Windows (cp1252) pueden romper con caracteres no-ASCII.
    # Se fuerza UTF-8 con fallback seguro.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    os.makedirs(os.path.dirname(ARCHIVO_LOG), exist_ok=True)

    root = logging.getLogger()
    root.setLevel(nivel)

    # Evitar duplicar handlers si se llama dos veces
    if root.handlers:
        return root

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    archivo = logging.FileHandler(ARCHIVO_LOG, encoding="utf-8")
    archivo.setFormatter(formato)

    root.addHandler(consola)
    root.addHandler(archivo)
    return root
