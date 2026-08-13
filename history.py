"""
history.py
==========
Historial persistente de vacantes (SQLite) para métricas.

Responsabilidad ÚNICA de este archivo:
    - Guardar cada vacante detectada con su metadata (plan, categoría,
      fuente, modalidad, ...).
    - Permitir consultar métricas (vacantes por semana/plan/fuente).
    - Registrar el estado de postulación (CU-06).

Usa SQLite (stdlib) -> un solo archivo, sin servidor, consultable.
"""
import os
import sqlite3

from config import ARCHIVO_HISTORIAL

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vacantes (
    url             TEXT PRIMARY KEY,
    plan            TEXT,
    categoria       TEXT,
    fuente          TEXT,
    titulo          TEXT,
    empresa         TEXT,
    ubicacion       TEXT,
    modalidad       TEXT,
    idioma_es       INTEGER,
    coincidencias   INTEGER,
    terminos_match  TEXT,
    fecha_detectada TEXT,
    estado          TEXT DEFAULT 'detectada'
);
"""


def _conexion():
    os.makedirs(os.path.dirname(ARCHIVO_HISTORIAL), exist_ok=True)
    conn = sqlite3.connect(ARCHIVO_HISTORIAL)
    conn.execute(_SCHEMA)
    return conn


def registrar_vacantes(vacantes, estado="detectada"):
    """
    Inserta vacantes (listas de dicts, calificadas o rechazadas).
    INSERT OR IGNORE: no rompe corridas por URLs ya conocidas.
    """
    if not vacantes:
        return 0

    filas = [
        (
            v["url"],
            v.get("plan", ""),
            v.get("categoria", ""),
            v.get("sitio_origen", ""),
            v.get("titulo", ""),
            v.get("empresa", ""),
            v.get("ubicacion", ""),
            v.get("modalidad", ""),
            1 if v.get("idioma_es") else 0,
            v.get("coincidencias", 0),
            v.get("terminos_match", ""),
            v.get("fecha_detectada", ""),
            estado,
        )
        for v in vacantes
        if v.get("url")
    ]

    with _conexion() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO vacantes
               (url, plan, categoria, fuente, titulo, empresa, ubicacion,
                modalidad, idioma_es, coincidencias, terminos_match,
                fecha_detectada, estado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            filas,
        )
    return len(filas)


def registrar_rechazadas(rechazadas):
    """Guarda las "casi califican" con estado 'revision' para métricas."""
    for v in rechazadas:
        v["modalidad"] = v.get("modalidad", "presencial")
    return registrar_vacantes(rechazadas, estado="revision")


def actualizar_estado(url, estado):
    """Marca una vacante (ej: 'postulada')."""
    with _conexion() as conn:
        conn.execute(
            "UPDATE vacantes SET estado = ? WHERE url = ?", (estado, url)
        )


def vacantes_por_semana(plan=None):
    """Conteo de vacantes detectadas agrupadas por semana."""
    sql = """
        SELECT substr(fecha_detectada, 1, 10) AS dia,
               COUNT(*) AS total
        FROM vacantes
        WHERE estado != 'revision'
    """
    params = ()
    if plan:
        sql += " AND plan = ?"
        params = (plan,)
    sql += " GROUP BY dia ORDER BY dia DESC LIMIT 12"

    with _conexion() as conn:
        return conn.execute(sql, params).fetchall()


def resumen_por_plan():
    """Conteo por plan para el resumen de corrida."""
    with _conexion() as conn:
        return conn.execute(
            "SELECT plan, COUNT(*) FROM vacantes GROUP BY plan ORDER BY plan"
        ).fetchall()


def obtener_registros(estado=None):
    """
    Devuelve los registros del historial como listas de dicts compatibles
    con alerts.construir_html / construir_html_rechazadas.
    Se usa para reenviar resultados ya guardados sin re-scrapear.
    """
    cols = [
        "url", "plan", "categoria", "fuente", "titulo", "empresa",
        "ubicacion", "modalidad", "idioma_es", "coincidencias",
        "terminos_match", "fecha_detectada", "estado",
    ]
    sql = "SELECT " + ", ".join(cols) + " FROM vacantes"
    params = ()
    if estado:
        sql += " WHERE estado = ?"
        params = (estado,)
    sql += " ORDER BY fecha_detectada DESC"

    with _conexion() as conn:
        filas = conn.execute(sql, params).fetchall()

    registros = []
    for fila in filas:
        d = dict(zip(cols, fila))
        d["idioma_es"] = bool(d.get("idioma_es"))
        registros.append(d)
    return registros


def imprimir_resumen():
    """Resumen legible para el final de cada corrida."""
    print("\n  [METRICAS] Historial acumulado:")
    for plan, total in resumen_por_plan():
        print(f"     Plan {plan}: {total} vacantes")
    semanal = vacantes_por_semana()
    if semanal:
        dia, total = semanal[0]
        print(f"     Último día con detecciones: {dia} ({total})")


if __name__ == "__main__":
    imprimir_resumen()
