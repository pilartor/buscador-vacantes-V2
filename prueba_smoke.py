"""
prueba_smoke.py
===============
Prueba de humo del pipeline COMPLETO con datos simulados.

- No hace llamadas de red (monkeypatch de source.extraer_jobs_categoria).
- No envía emails (NOTIFICACION_CANAL=consola).
- Verifica: extracción simulada -> transform -> dedup -> historial
  SQLite -> notificación en consola -> guardado de vistos.

Uso:
    python prueba_smoke.py
"""
import os

# Canal consola y fuentes secundarias OFF antes de importar el proyecto
os.environ["NOTIFICACION_CANAL"] = "consola"

import config  # noqa: E402
config.FUENTES_SECUNDARIAS = []

# Estado aislado en un directorio temporal (no tocar Data/ del proyecto)
import tempfile  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="jobbot_smoke_")
config.ARCHIVO_VISTOS = os.path.join(_TMP, "vacantes_vistas.json")
config.ARCHIVO_HISTORIAL = os.path.join(_TMP, "historial.db")
config.ARCHIVO_LOG = os.path.join(_TMP, "corridas.log")

# ── Datos simulados por categoría ──
# Umbrales: IDMC=1, SOPORT=3, ETL=2, QA=2
FAKE_CRUDOS = {
    "IDMC": [
        {
            "categoria": "IDMC", "pais_busqueda": "Argentina", "requiere_remoto": False,
            "titulo": "Data Engineer Informatica IDMC",
            "empresa": "Banco Test", "ubicacion": "CABA, Argentina",
            "descripcion": "Buscamos Data Engineer con experiencia en Informatica IDMC, "
                           "IICS y Cloud Data Integration. Modalidad híbrida. Beneficios, "
                           "vacante full time. Postularse con CV.",
            "url": "https://linkedin.com/jobs/view/FAKE-IDMC-1",
            "is_remote_flag": True, "sitio_origen": "linkedin",
        },
        {
            "categoria": "IDMC", "pais_busqueda": "Argentina", "requiere_remoto": False,
            "titulo": "Sr Data Engineer",
            "empresa": "Otro", "ubicacion": "CABA, Argentina",
            "descripcion": "Ingles avanzado, experiencia en PowerCenter, beneficios, "
                           "vacante interesante para postularse, desarrollo.",
            "url": "https://linkedin.com/jobs/view/FAKE-IDMC-2",
            "is_remote_flag": False, "sitio_origen": "linkedin",
        },
    ],
    "SOPORT": [
        {
            "categoria": "SOPORT", "pais_busqueda": "Argentina", "requiere_remoto": False,
            "titulo": "Analista de base de datos",
            "empresa": "Empresa Test", "ubicacion": "La Plata, Argentina",
            "descripcion": "Monitoreo de queries SQL en la base, reportes para el equipo. "
                           "Beneficios, vacante, postularse, experiencia.",
            "url": "https://linkedin.com/jobs/view/FAKE-SOPORT-1",
            "is_remote_flag": False, "sitio_origen": "linkedin",
        },
    ],
    "ETL": [
        {
            "categoria": "ETL", "pais_busqueda": "Argentina", "requiere_remoto": False,
            "titulo": "Data Engineer - Snowflake ETL",
            "empresa": "Consultora Test", "ubicacion": "Buenos Aires, Argentina",
            "descripcion": "Buscamos Data Engineer con python, ETL, Snowflake y pipelines "
                           "de datos. Trabajo remoto. Beneficios, experiencia, postularse.",
            "url": "https://linkedin.com/jobs/view/FAKE-ETL-1",
            "is_remote_flag": False, "sitio_origen": "indeed",
        },
        {
            "categoria": "ETL", "pais_busqueda": "Argentina", "requiere_remoto": False,
            "titulo": "Analista administrativo",
            "empresa": "NoMatch", "ubicacion": "CABA, Argentina",
            "descripcion": "Excelente oportunidad con beneficios, vacante para "
                           "postularse, equipo de desarrollo.",
            "url": "https://linkedin.com/jobs/view/FAKE-ETL-2",
            "is_remote_flag": False, "sitio_origen": "linkedin",
        },
    ],
    "QA": [],
}


def fake_extraer(categoria):
    print(f"   [SMOKE] retornando crudos simulados para '{categoria}'")
    return list(FAKE_CRUDOS.get(categoria, []))


def main():
    from logging_config import setup_logging
    setup_logging()

    import source
    source.extraer_jobs_categoria = fake_extraer

    from pipeline import ejecutar_corrida

    print("=" * 70)
    print("SMOKE TEST: pipeline completo con datos simulados")
    print("=" * 70)

    resultado = ejecutar_corrida(planes=None)

    # 3 calificadas (IDMC-1, IDMC-2, ETL-1) + 1 rechazada (SOPORT-1, "casi califica")
    assert resultado["nuevas_calificadas"] == 3, (
        f"Se esperaban 3 calificadas, hay {resultado['nuevas_calificadas']}"
    )
    assert resultado["nuevas_rechazadas"] == 1, (
        f"SOPORT-1 debería caer en 'casi califican' (2 matches < umbral 3), hay "
        f"{resultado['nuevas_rechazadas']}"
    )

    # Idempotencia: una segunda corrida no debe notificar las mismas URLs
    print("\n--- SEGUNDA CORRIDA (debe devolver 0 nuevas) ---")
    resultado2 = ejecutar_corrida(planes=None)
    assert resultado2["nuevas_calificadas"] == 0, "La dedup debería evitar reenvíos"
    assert resultado2["nuevas_rechazadas"] == 0

    # Historial consultable
    from history import vacantes_por_semana, resumen_por_plan
    print("\nHistorial por plan:", resumen_por_plan())
    print("Última semana:", vacantes_por_semana())

    print("\n✅ SMOKE TEST OK")


if __name__ == "__main__":
    main()
