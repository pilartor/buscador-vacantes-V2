"""
pipeline.py
===========
Orquesta UNA corrida completa del proceso:

    config (categorías)
        -> source.extraer_jobs_categoria()        [EXTRACT]
        -> transform.transformar_categoria()       [TRANSFORM]
        -> cache (filtrar "ya vistos")             [STATE]
        -> alerts.notificar() (calificadas y "casi califican") [LOAD]
        -> history (historial SQLite + métricas)   [STATE]
        -> cache.guardar_vistos()                  [STATE]

Este archivo NO sabe CÓMO se scrapea, CÓMO se filtra, ni CÓMO se
notifica -- solo conoce el ORDEN en que ocurren esas cosas.
"""
import logging
from datetime import datetime

from config import TERMINOS, CATEGORIA_A_PLAN, EMAIL_ASUNTO, EMAIL_ASUNTO_RECHAZADAS
from source import extraer_jobs_categoria
from transform import transformar_categoria
from cache import cargar_vistos, guardar_vistos
from history import registrar_vacantes, registrar_rechazadas, imprimir_resumen
from alerts import construir_html, construir_html_rechazadas, notificar

log = logging.getLogger("pipeline")


def _cabecera(mensaje):
    print(f"\n{'#' * 70}")
    print(f"#  {mensaje}")
    print(f"{'#' * 70}")


def ejecutar_corrida(planes=None):
    """
    Ejecuta una corrida completa.

    planes: lista opcional de Planes (ej ["A", "C"]). Si es None/[] se
    procesan todas las categorías.
    """
    inicio = datetime.now()
    _cabecera(f"INICIANDO CORRIDA — {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Corrida iniciada (planes: {planes or 'TODOS'})")

    # ── Paso 1: cargar vistos ──
    vistos = cargar_vistos()
    print(f"  URLs ya vistas (ventana de retención): {len(vistos)}")

    # ── Paso 2: extraer + transformar, por categoría ──
    todas_calificadas = []
    todas_rechazadas = []
    vistos_corrida = set()

    categorias_activas = [
        c for c in TERMINOS
        if not planes or CATEGORIA_A_PLAN[c] in planes
    ]

    for categoria in categorias_activas:
        print(f"\n--- Categoría: {categoria} (Plan {CATEGORIA_A_PLAN[categoria]}) ---")

        crudas = extraer_jobs_categoria(categoria)
        print(f"  Crudas: {len(crudas)}")

        calificadas, rechazadas = transformar_categoria(
            crudas, categoria, vistos_corrida
        )
        print(f"  Calificadas: {len(calificadas)} | "
              f"Rechazadas (AR, casi califican): {len(rechazadas)}")

        vistos_corrida.update(v["url"] for v in calificadas)
        vistos_corrida.update(v["url"] for v in rechazadas)

        todas_calificadas.extend(calificadas)
        todas_rechazadas.extend(rechazadas)

    # ── Paso 3: filtrar solo las NUEVAS (no vistas antes) ──
    nuevas_calificadas = [v for v in todas_calificadas if v["url"] not in vistos]
    nuevas_rechazadas = [v for v in todas_rechazadas if v["url"] not in vistos]

    print(f"\n  Total calificadas: {len(todas_calificadas)} | "
          f"NUEVAS: {len(nuevas_calificadas)}")
    print(f"  Total rechazadas:  {len(todas_rechazadas)} | "
          f"NUEVAS: {len(nuevas_rechazadas)}")

    # ── Paso 4: notificar calificadas nuevas ──
    html_calificadas = construir_html(nuevas_calificadas)
    notificar(html_calificadas, len(nuevas_calificadas), EMAIL_ASUNTO)

    # ── Paso 5: notificar rechazadas nuevas (Argentina) ──
    html_rechazadas = construir_html_rechazadas(nuevas_rechazadas)
    notificar(html_rechazadas, len(nuevas_rechazadas), EMAIL_ASUNTO_RECHAZADAS)

    # ── Paso 6: historial SQLite (métricas) ──
    registradas = registrar_vacantes(nuevas_calificadas, estado="detectada")
    registradas_rech = registrar_rechazadas(nuevas_rechazadas)
    print(f"  [SAVE] Historial: {registradas} calificadas + "
          f"{registradas_rech} 'casi califican'")

    # ── Paso 7: actualizar "vistos" con TODO lo de esta corrida ──
    guardar_vistos(vistos_corrida)
    print(f"  [SAVE] 'vistos' actualizado. Total URLs en esta corrida: {len(vistos_corrida)}")

    # ── Paso 8: resumen ──
    imprimir_resumen()

    duracion = (datetime.now() - inicio).total_seconds()
    log.info(f"Corrida finalizada en {duracion:.1f}s "
             f"(calificadas nuevas: {len(nuevas_calificadas)})")

    _cabecera(f"CORRIDA FINALIZADA — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return {
        "nuevas_calificadas": len(nuevas_calificadas),
        "nuevas_rechazadas": len(nuevas_rechazadas),
        "duracion_seg": round(duracion, 1),
    }


def reenviar_resultado():
    """
    Envía email con los resultados YA persistidos en el historial
    (sin re-scrapear). Útil para reenviar una corrida anterior.
    """
    from history import obtener_registros

    calificadas = obtener_registros(estado="detectada")
    rechazadas = obtener_registros(estado="revision")

    if not calificadas and not rechazadas:
        print("No hay resultados guardados en el historial.")
        return 0

    html_c = construir_html(calificadas)
    notificar(html_c, len(calificadas), EMAIL_ASUNTO)

    html_r = construir_html_rechazadas(rechazadas)
    notificar(html_r, len(rechazadas), EMAIL_ASUNTO_RECHAZADAS)

    print(f"  [REVIVO] Reenvío de historial: {len(calificadas)} calificadas "
          f"+ {len(rechazadas)} 'casi califican'")
    return len(calificadas) + len(rechazadas)


if __name__ == "__main__":
    from logging_config import setup_logging

    setup_logging()
    ejecutar_corrida()
