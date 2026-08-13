"""
config.py
=========
Configuración central del proyecto.

Acá viven SOLO datos declarativos: credenciales, términos de búsqueda,
umbrales, países, horarios, fuentes secundarias y parámetros de
notificación. No hay lógica de negocio en este archivo.

Los secretos se leen desde variables de entorno (.env); nunca se
hardcodean.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  RUTAS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
os.makedirs(DATA_DIR, exist_ok=True)

ARCHIVO_VISTOS     = os.path.join(DATA_DIR, "vacantes_vistas.json")
ARCHIVO_HISTORIAL  = os.path.join(DATA_DIR, "historial.db")
ARCHIVO_LOG        = os.path.join(DATA_DIR, "corridas.log")

# ─────────────────────────────────────────────
#  CONFIG EMAIL (Gmail)
# ─────────────────────────────────────────────
EMAIL_APP_PASSWORD  = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_REMITENTE     = os.getenv("EMAIL_REMITENTE")
EMAIL_DESTINATARIO  = os.getenv("EMAIL_DESTINATARIO") or EMAIL_REMITENTE

EMAIL_ASUNTO             = "Vacantes nuevas - Plan A/B/C/D"
EMAIL_ASUNTO_RECHAZADAS  = "Vacantes rechazadas (Argentina, casi califican)"

# ─────────────────────────────────────────────
#  NOTIFICACIÓN (LOAD intercambiable)
# ─────────────────────────────────────────────
# Canales soportados: "email" | "consola"
NOTIFICACION_CANAL = os.getenv("NOTIFICACION_CANAL", "email").lower()

# ─────────────────────────────────────────────
#  CONFIG GENERAL
# ─────────────────────────────────────────────
SITIOS_BUSQUEDA        = ["linkedin", "indeed"]
CANTIDAD_POR_BUSQUEDA  = 25
HORAS_ANTIGUEDAD       = 48
PAUSA_ENTRE_BUSQUEDAS  = 2          # segundos entre búsquedas (anti-bloqueo)
MIN_MATCHES_POR_CATEGORIA = {
    "IDMC":  1,
    "SOPORT": 3,
    "ETL":   2,
    "QA":    2,
}
DEBUG = True

# Retención: cuántos días se recuerdan las URLs ya vistas antes de olvidarlas
RETENCION_DIAS_VISTOS = 90

# Horarios fijos de ejecución (formato 24hs "HH:MM")
HORARIOS_EJECUCION = ["10:00", "15:00", "17:00"]

# ─────────────────────────────────────────────
#  FUENTES SECUNDARIAS (v2 - bajo riesgo)
# ─────────────────────────────────────────────
# Conectores activos: "remotive" | "ats" | "rss" | "computrabajo" | "spa"
FUENTES_SECUNDARIAS = ["computrabajo", "ats", "remotive", "spa", "rss"]

# Máximo de términos de la categoría que se usan para construir la query
SECUNDARIAS_MAX_TERMINOS = 5

REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"

# Plataformas ATS con API pública de lecturas (slug = nombre público de la empresa)
#   Workable:        https://apply.workable.com/api/v1/widget/companies/{slug}
#   Lever:           https://api.lever.co/v0/postings/{slug}?mode=json
#   Greenhouse:      https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
#   SmartRecruiters: https://api.smartrecruiters.com/v1/companies/{slug}/postings
# Para encontrar el slug: entrá a la web de empleos de la empresa y buscá la
# API / página de la plataforma que usa (Workable, Lever, Greenhouse...).
ATS_WORKABLE = ["tu-empresa"]   # ej: apply.workable.com/{slug}
ATS_LEVER    = []               # ej: api.lever.co/v0/postings/{slug}
ATS_GREENHOUSE = []             # ej: boards.greenhouse.io/{slug}
ATS_SMARTRECRUITERS = []        # ej: api.smartrecruiters.com/v1/companies/{slug}

# Si True, SmartRecruiters baja la descripción completa por aviso (más lento
# pero permite el filtrado de rol). Si False, solo usa el listado (sin desc).
ATS_DETALLE_DESCRIPCION = True

# ─────────────────────────────────────────────
#  COMPUTRABAJO (bolsa LATAM multi-país, HTTP puro)
# ─────────────────────────────────────────────
# Países activos (subdominio de 2 letras de computrabajo.com).
COMPUTRABAJO_PAISES = ["ar", "cl", "mx", "co", "pe", "uy", "ec", "bo"]
# Países por plan: Plan A (IDMC) busca en todos los países; B/C/D solo AR.
COMPUTRABAJO_PAISES_POR_PLAN = {
    "IDMC":   COMPUTRABAJO_PAISES,
    "SOPORT": ["ar"],
    "ETL":    ["ar"],
    "QA":     ["ar"],
}
# Máximo de ofertas a procesar (con descripción) por (país, término).
COMPUTRABAJO_MAX_POR_BUSQUEDA = 8
# Términos de búsqueda por categoría (se slugifican para la URL).
COMPUTRABAJO_TERMINOS = {
    "IDMC":   ["informatica", "idmc", "iics", "powercenter"],
    "SOPORT": ["soporte etl", "soporte informatica"],
    "ETL":    ["data engineer", "etl developer", "ingeniero de datos", "data warehouse"],
    "QA":     ["data quality", "data governance", "master data"],
}

# ─────────────────────────────────────────────
#  FUENTES SPA (requieren navegador headless)
# ─────────────────────────────────────────────
# Conectores activos: "bumeran" | "zonajobs"
# Nota: estas bolsas renderizan todo con JavaScript (SPA), por lo que se
# consumen con Playwright (chromium). Si Playwright no está instalado,
# el conector saltea la fuente sin romper la corrida.
FUENTES_SPA = ["bumeran", "zonajobs"]
SPA_MAX_POR_BUSQUEDA = 10

# Formato real de la URL de búsqueda: /empleos-busqueda-{keyword}.html
# (la ruta /busquedas/empleos-de-{kw} responde 404 y cae al fallback
# "Últimos empleos publicados", sin resultados del keyword).
SPA_CONFIG = {
    "bumeran": {
        "base_url": "https://www.bumeran.com.ar/empleos-busqueda-{slug}.html",
        "card": 'a[href*="/empleos/"]',
    },
    "zonajobs": {
        "base_url": "https://www.zonajobs.com.ar/empleos-busqueda-{slug}.html",
        "card": 'a[href*="/empleos/"]',
    },
}
SPA_TERMINOS = {
    "IDMC":   ["informatica", "idmc"],
    "SOPORT": ["soporte etl"],
    "ETL":    ["data engineer", "etl developer"],
    "QA":     ["data quality"],
}
# Espera (ms) a que la SPA cargue los resultados antes de extraer.
SPA_TIMEOUT_MS = 12000

# Feeds RSS (Workable publica feeds, tablones, etc.)
RSS_FEEDS = ["https://remotive.com/remote-jobs/feed"]

# ─────────────────────────────────────────────
#  CATEGORÍAS -> PLAN
# ─────────────────────────────────────────────
CATEGORIA_A_PLAN = {
    "IDMC":   "A",
    "SOPORT": "B",
    "ETL":    "C",
    "QA":     "D",
}

TERMINOS = {
    "IDMC": [
        "Informatica Cloud", "IDMC/IICS", "IICS/IDMC",
        "IICS", "iics", "idmc", "IDMC", "CAI", "Informatica Cloud Application Integration",
        "CDI", "Cloud Data Integration", "cloud data integration", "powercenter", "PowerCenter", "Power Center",
        "informatica powercenter", "API Center", "API Manager", "Process Designer", "CDI/PC",
        "informatica", "Informatica Developer", "informatica admin", "informatica administration",
        "informatica mdm", "data integration", "cloud integration", "data migration",
    ],
    "SOPORT": [
        "ETL", "ELT", "SQL", "monitoreo", "user FTP", "FTP",
        "administracion", "soporte", "desarrollo de pipelines",
        "SLA", "roles", "usuarios", "agentes", "conexiones",
        "plataforma de datos", "administración de plataforma", "soporte tecnico",
        "soporte de datos", "soporte informatico", "soporte etl",
        "data operations", "dataops", "operaciones de datos",
        "control-m", "job scheduler", "monitoreo de procesos",
        "incidentes", "tickets",
    ],
    "ETL": [
        "ETL/ELT", "ETL", "desarrollador ETL", "Developer ETL",
        "Snowflake", "Medallion", "DWH", "Data Engineer Python",
        "pipeline de datos", "data pipeline", "Data Engineer", "DataEngineer", "pipeline", "scraping",
        "Data Integration", "Integración de datos", "python",
        "Airflow", "Redshift", "Teradata", "Control-M", "AWS Glue",
        "ingeniero de datos", "ingeniera de datos", "data engineering",
        "etl developer", "data warehouse", "big data", "informatica",
        "ingeniería de datos", "ingenieria de datos", "ingenieros de datos",
        "big data engineer", "data platform engineer", "data pipeline engineer",
        "data integration engineer", "analytics engineer", "data analytics engineer",
        "etl manager", "etl lead", "etl specialist", "etl engineering",
        "data warehouse engineer", "dwh engineer",
        "spark", "pyspark", "databricks", "dbt", "kafka", "hadoop",
        "glue", "lambda", "bigquery", "synapse", "azure data factory", "adf",
        "talend", "pentaho", "ssis", "datastage", "oracle",
        "sql server", "pl/sql", "postgres",
        "data ingestion", "ingesta de datos", "ingestion de datos",
        "data lake", "data ops", "dataops",
    ],
    "QA": [
        "Data Quality", "Data Governance", "Cloud Migration Engineer",
        "Data Validation", "QA Data", "Data Steward",
        "Validación de datos", "Gobierno de Datos", "iics", "idmc", "PowerCenter",
        "Calidad de datos", "Master Data Management", "MDM",
        "profiling", "metadata management", "source to target", "origen a destino",
        "data quality engineer", "data governance",
        "data quality analyst", "calidad del dato", "data observability",
        "observabilidad de datos", "data lineage", "linaje de datos",
        "data catalog", "catalogo de datos", "catálogo de datos",
        "data contract", "contrato de datos", "reconciliación", "reconciliacion",
        "reconciliation", "business glossary", "glosario de negocio",
        "data profiling", "great expectations",
    ],
}

PAISES_HISPANOS_REMOTO = [
    "Chile", "Peru", "Mexico", "Colombia", "Uruguay",
    "Costa Rica", "Spain", "Venezuela", "Ecuador", "Panama", "Worldwide",
]

PLANES_PAISES = {
    "IDMC":   [("Argentina", False)] + [(p, False) for p in PAISES_HISPANOS_REMOTO],
    "SOPORT": [("Argentina", False)],
    "ETL":    [("Argentina", False)],
    "QA":     [("Argentina", False)],
}

# ─────────────────────────────────────────────
#  MODALIDAD (keywords priorizadas)
# ─────────────────────────────────────────────
REMOTE_KEYWORDS = [
    "remote", "remoto", "100% remoto", "full remote", "trabajo remoto",
    "home office", "teletrabajo", "work from home", "wfh", "open to latam",
    "ubicación: remoto", "remota",
]
HYBRID_KEYWORDS = ["híbrid", "hibrid", "hybrid", "mixto"]
PRESENCIAL_KEYWORDS = ["presencial", "on-site", "onsite", "en sitio", "in office", "en oficina"]

# ─────────────────────────────────────────────
#  MOTOR DE ROL (análisis de lenguaje natural del body)
#  Decide si el cuerpo de la vacante es de ingeniería de datos
#  según el perfil/stack del CV (Pilar Torres · Data Engineer).
# ─────────────────────────────────────────────
# Peso extra por término de TERMINOS (default = 1).
# Los términos núcleo del CV pesan más al puntuar.
KEYWORDS_PESO = {
    "IDMC":   {"idmc": 4, "iics": 4, "powercenter": 4, "informatica cloud": 4, "cai": 3, "api center": 2, "api manager": 2, "informatica": 2},
    "SOPORT": {"soporte": 3, "monitoreo": 2, "sla": 2, "conexiones": 2, "agentes": 2, "plataforma": 1},
    "ETL":    {"data engineer": 4, "snowflake": 3, "etl": 3, "python": 2, "dwh": 2, "airflow": 2, "redshift": 2, "control-m": 2, "informatica": 2, "etl developer": 4, "data warehouse": 2, "big data": 2, "spark": 2, "pyspark": 3, "databricks": 3, "dbt": 2, "kafka": 2, "talend": 2, "pentaho": 2, "bigquery": 2, "synapse": 2, "oracle": 1, "data lake": 2, "data engineering": 2, "analytics engineer": 2, "data platform engineer": 2},
    "QA":     {"data quality": 3, "data governance": 3, "mdm": 2, "profiling": 2, "data steward": 2, "data lineage": 2, "data catalog": 2, "data observability": 2, "data contract": 2},
}

# Frases/raíces que confirman un perfil de datos para cada Plan.
# La raíz "informatic" cubre Informatica, Informática, Informatica Cloud...
SENALES_ROL = {
    "IDMC": [
        "informatic", "idmc", "iics", "powercenter", "power center", "cai",
        "data integration", "cloud data integration", "cdi",
        "integración de datos", "integracion de datos", "data migration",
        "api center", "api manager", "mapping", "scd", "metadata",
        "informatica mdm",
    ],
    "SOPORT": [
        "soporte", "sla", "monitoreo", "administración de plataforma",
        "administracion de plataforma", "roles", "usuarios", "agentes",
        "conexiones", "informatic", "soporte de datos", "data operations",
        "dataops", "operaciones de datos", "control-m", "job scheduler",
        "ticket", "incidente",
    ],
    "ETL": [
        "data engineer", "ingeniero de datos", "ingeniera de datos",
        "ingenieros de datos", "ingeniería de datos", "ingenieria de datos",
        "etl", "elt", "data warehouse", "dwh", "data warehouse engineer",
        "pipeline", "pipelines", "snowflake", "medallion", "informatic",
        "aws glue", "glue", "lambda", "redshift", "teradata", "control-m",
        "source to target", "origen a destino", "oracle",
        "integración de datos", "integracion de datos", "airflow",
        "spark", "pyspark", "databricks", "dbt", "kafka", "data lake",
        "data ingestion", "ingesta de datos", "big data", "talend",
        "pentaho", "ssis", "datastage", "data ops", "dataops",
        "bigquery", "synapse", "azure data factory", "sql server",
        "postgres", "analytics engineer", "data platform engineer",
        "data integration engineer", "data pipeline engineer",
    ],
    "QA": [
        "data quality", "calidad de datos", "calidad del dato",
        "data governance", "gobierno de datos",
        "validación de datos", "validacion de datos", "data steward",
        "mdm", "master data", "profiling", "scd", "metadata",
        "data lineage", "linaje de datos", "data catalog",
        "catalogo de datos", "catálogo de datos", "data observability",
        "observabilidad", "data contract", "contrato de datos",
        "business glossary", "glosario de negocio",
        "reconciliation", "reconciliacion", "reconciliación",
    ],
}
PESO_SENAL_ROL = 3

# Señales de roles que NO son Data Engineer (falsos positivos típicos).
SENALES_NEGATIVAS = [
    "frontend", "front-end", "react", "angular", "vue", "fullstack",
    "full-stack", "desarrollo java", "java developer", "programador java",
    "back office", "ventas", "comercial", "marketing", "copywriter",
    "publicidad", "actuarial", "actuario", "seguros", "reclutamiento",
    "talent acquisition", "recursos humanos", "rrhh", "contable",
    "impuestos", "cuentas a pagar", "payroll", "sueldos", "docente",
    "profesor", "enseñanza", "teacher", "diseñador", "designer",
    "ux/ui", "ui/ux", "content reviewer", "data labeling", "customer service",
    "soporte al cliente", "atención al cliente", "chef", "cocinero",
    "limpieza", "seguridad", "guardia", "conductor", "administrativo",
    "secretaria", "office assistant",
]
PENALIDAD_NEGATIVA = 4

# Puntaje mínimo ponderado por categoría para considerar la vacante
# del perfil (además de MIN_MATCHES_POR_CATEGORIA).
UMBRAL_SCORE = {"IDMC": 7, "SOPORT": 5, "ETL": 8, "QA": 6}
