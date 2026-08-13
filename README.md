# Job Alert Bot — Data Engineer Vacancy Finder

Bot personal de búsqueda de empleo que automatiza la detección de vacantes relevantes para un perfil de **Data Engineer**, las clasifica en **Planes A/B/C/D**, evita duplicados y notifica por email solo los resultados nuevos.

Evolución del modelo `Linkedin_Automatizacion` según el documento [`especificaciones_funcionales.md`](especificaciones_funcionales.md).

## ¿Qué hace?

1. **Extrae** vacantes de múltiples fuentes bajo el mismo contrato de datos:
   - **LinkedIn + Indeed** vía [JobSpy](https://github.com/Bunsly/JobSpy).
   - **Computrabajo** (LATAM multi-país: AR, CL, MX, CO, PE, UY, EC, BO) con HTTP puro.
   - **Bumeran / ZonaJobs** (SPA con Playwright chromium headless).
   - **Remotive** (API pública), **ATS de empresas** (Workable/Lever/Greenhouse/SmartRecruiters) y **feeds RSS**.
2. **Transforma**: filtra por relevancia (coincidencias técnicas + señales de rol positivas/negativas), detecta idioma (español), y **categoriza modalidad** (`remoto` / `hibrido` / `presencial`).
3. **Clasifica** cada vacante en un Plan (A/B/C/D) según el perfil de búsqueda:
   - Plan A = IDMC, Plan B = Soporte, Plan C = ETL, Plan D = QA.
4. **Evita duplicados** con retención de 90 días (`Data/vacantes_vistas.json`).
5. **Registra historial** en SQLite (`Data/historial.db`) para métricas.
6. **Notifica** por el canal configurado: email (Gmail SMTP) o consola (pruebas).
7. **Se ejecuta** manualmente (`--once`), solo algunos planes (`--plans`), programado (10:00, 15:00, 17:00) o por GitHub Actions (cron).

## Arquitectura (patrón ETL modular)

```
proyecto/
├── config.py          # Datos declarativos: términos, umbrales, países, fuentes, horarios
├── source.py          # EXTRACT: fachada de fuentes (JobSpy + secundarias)
├── sources/
│   ├── base.py        # Contrato común del dict "crudo"
│   ├── computrabajo.py# Conector Computrabajo (LATAM multi-país, HTTP)
│   ├── spa.py         # Conector Bumeran/ZonaJobs (Playwright chromium)
│   ├── remotive.py    # Conector API Remotive
│   ├── ats.py         # Conectores Workable / Lever / Greenhouse / SmartRecruiters
│   └── rss.py         # Conector feeds RSS
├── transform.py       # TRANSFORM: relevancia, señales de rol, idioma, modalidad, Plan
├── cache.py           # ESTADO: deduplicación con retención (JSON)
├── history.py         # ESTADO: historial SQLite + métricas
├── alerts.py          # LOAD: HTML + notificador intercambiable (email/consola)
├── pipeline.py        # Orquestador de una corrida
├── main.py            # Entrada: --once, --plans, modo programado
├── logging_config.py  # Log en consola + Data/corridas.log
└── Data/              # Estado generado en runtime (no versionado)
```

## Requisitos

```bash
pip install -r requirements.txt
```

## Configuración

1. `cp .env.example .env`
2. Para email: activar verificación en 2 pasos en Gmail y generar una contraseña de aplicación (https://myaccount.google.com/apppasswords). Completar `EMAIL_REMITENTE` y `EMAIL_APP_PASSWORD`.
3. Para probar sin Gmail: `NOTIFICACION_CANAL=consola`.
4. Opcional: completar `ATS_WORKABLE` / `ATS_LEVER` / `RSS_FEEDS` en `config.py` con las empresas objetivo.

## Uso

```bash
python main.py --once            # corrida manual (todas las categorías)
python main.py --once --plans A C  # solo Planes A y C
python main.py                   # modo programado (10:00 / 15:00 / 17:00)
```

Pruebas aisladas de módulos (sin red ni email):

```bash
python transform.py              # transform con datos de ejemplo
python alerts.py                 # notificador de ejemplo
python cache.py                  # estado de vistos
python history.py                # resumen de métricas
python prueba_smoke.py           # pipeline completo con datos simulados
```

## Fuentes y riesgos

- Las fuentes secundarias elegidas son de **bajo riesgo** (APIs públicas y feeds). Se descartó expresamente el scraping de perfiles personales de reclutadores en LinkedIn por riesgo de bloqueo de cuenta/IP y violación de términos de servicio (ver §7.7 del documento de especificaciones).
- Se aplican pausas entre búsquedas para reducir la probabilidad de bloqueos.

## Decisiones de diseño

- **Módulos con responsabilidad única** y contrato de datos común: agregar una fuente no toca transform/alertas.
- **Deduplicación por URL** con ventana de retención (90 días).
- **Modalidad priorizada por reglas**: keywords presencial/híbrido pesan más que el flag de la fuente.
- **Clasificación declarativa** por config: agregar un Plan no requiere tocar lógica.
- **Notificador intercambiable**: email/consola hoy, Slack/Telegram mañana.

## Roadmap

- F1 (base): JobSpy LinkedIn+Indeed, planes A/B/C/D, email, dedup, schedule ✅
- F2: modalidad categorizada, historial SQLite, retención, `--plans`, log persistente ✅
- F3: conectores Remotive / ATS / RSS ✅
- F4: conectores Computrabajo (LATAM multi-país) y SPA (Bumeran/ZonaJobs) ✅
- F5: GitHub Actions con cron y persistencia de vistos ✅
- F6: dashboard con métricas de postulación 💡
- F7: notificador Slack/Telegram y sugerencia de postulación 💡
