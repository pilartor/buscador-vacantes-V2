# Especificaciones Funcionales — Automatización de Búsqueda de Empleo (Perfil Data Engineer)

| Campo | Valor |
|---|---|
| **Documento** | Especificación de Requerimientos Funcionales (SRS) |
| **Versión** | 1.0 |
| **Fecha** | 2026-08-12 |
| **Estado** | Borrador |
| **Autor** | Data Engineer (perfil de búsqueda) |
| **Repositorio base** | `Linkedin_Automatizacion` (modelo v1) |

---

## 1. Resumen ejecutivo

Este documento define las especificaciones funcionales de un **bot personal de búsqueda de empleo** orientado al perfil profesional de **Data Engineer**. El sistema detecta automáticamente vacantes relevantes publicadas en **LinkedIn** e **Indeed**, las enriquece, las clasifica por perfiles de búsqueda (Planes A/B/C/D), **evita duplicados** entre corridas y **notifica por email** solo los resultados nuevos.

El presente documento **evoluciona el modelo v1** existente (`Linkedin_Automatizacion`) incorporando:

- **Nuevas fuentes de captación** de bajo riesgo (tablones de empleo remoto, agregadores y feeds RSS de ATS).
- **Un diseño de datos más robusto** (esquema definido, trazabilidad, métricas de postulación).
- **Oportunidades de mejora** documentadas (orquestación cloud, dashboard, aplicaciones automáticas).

> ⚠️ **Nota de portafolio:** este documento funciona como **especificación funcional** y como **documentación técnica de arquitectura**, siguiendo el patrón ETL modular ya validado en la v1. Es material de presentación para entrevistas y revisiones técnicas.

---

## 2. Contexto y problema

Un profesional de datos en búsqueda activa necesita:

1. Detectar vacantes de **Data Engineer / ETL / IDMC** con rapidez (muchas publicaciones dejan de aceptar candidatos en menos de 48 horas).
2. Filtrar el ruido: la mayoría de resultados genéricos ("data", "engineer") no aplican al perfil.
3. Identificar modalidad real (**remoto / híbrido / presencial**) y **ubicación**.
4. **Priorizar** oportunidades según el plan de búsqueda activa (A/B/C/D).
5. **No repetir** revisión manual de vacantes ya vistas o descartadas.

### 2.1. Objetivos

| # | Objetivo | Métrica de éxito |
|---|---|---|
| O1 | Detectar vacantes nuevas relevantes en < 24 h desde su publicación | Tiempo promedio publicación → alerta |
| O2 | Reducir falsos positivos | % de vacantes notificadas que el usuario considera relevantes (> 70 %) |
| O3 | Cubrir múltiples canales (LinkedIn, Indeed, tablones remotos, agregadores) | N.º de fuentes activas |
| O4 | Eliminar trabajo manual repetitivo | Alertas 100 % automáticas, sin intervención |
| O5 | Generar historial consultable de vacantes y postulaciones | Dashboard o exporte con métricas |

### 2.2. Fuera de alcance (v1.0)

- Postulación automática a vacantes.
- Agendado de entrevistas.
- Análisis de mercado laboral (solo informativo posterior).
- Aplicación web pública.

---

## 3. Usuarios y casos de uso

### 3.1. Actores

| Actor | Descripción |
|---|---|
| **Usuario (Data Engineer)** | Propietario del bot; consume las alertas y el historial. |
| **Sistema (bot)** | Actor automático que ejecuta corridas ETL programadas. |

### 3.2. Casos de uso principales

| ID | Caso de uso | Actor | Descripción |
|---|---|---|---|
| CU-01 | Ejecutar corrida manual | Usuario | Correr una vez el pipeline completo (`--once`) para probar o forzar. |
| CU-02 | Ejecutar corrida programada | Sistema | Correr a horarios fijos (10:00, 15:00, 17:00) mientras la PC está encendida. |
| CU-03 | Recibir alerta de nuevas calificadas | Usuario | Email con tabla de vacantes nuevas que cumplen el mínimo de coincidencias. |
| CU-04 | Recibir alerta de "casi califican" | Usuario | Email separado con vacantes de Argentina, en español, con ≥ 1 coincidencia pero bajo el mínimo. |
| CU-05 | Consultar historial | Usuario | Ver métricas de vacantes por semana, plan y fuente. |
| CU-06 | Registrar postulación | Usuario | Marcar qué vacantes fueron postuladas (para métricas). |

---

## 4. Requerimientos funcionales

Cada requerimiento tiene un identificador único (**RF-n**) para trazabilidad. Se priorizan con **Alta / Media / Baja**.

### 4.1. Extracción de vacantes (EXTRACT)

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-01 | El sistema debe extraer vacantes desde **LinkedIn** e **Indeed** mediante la librería `JobSpy`. | Alta |
| RF-02 | Debe construir una **consulta OR** a partir de los términos técnicos configurados por categoría (ej: `"Informatica Cloud" OR "IDMC/IICS" OR ...`). | Alta |
| RF-03 | Debe ejecutar la búsqueda por **cada combinación de (país, requiere_remoto)** definida para la categoría. | Alta |
| RF-04 | Debe limitar la antigüedad de los resultados (`hours_old`, por defecto **48 h**) para priorizar vacantes recientes. | Alta |
| RF-05 | Debe limitar la cantidad de resultados por búsqueda (`results_wanted`, por defecto **25**). | Media |
| RF-06 | Debe capturar por vacante los campos crudos: `title`, `company`, `location`, `description`, `job_url`, `is_remote`, `site`. | Alta |
| RF-07 | Ante un error de red o de la fuente, la corrida de esa búsqueda debe **continuar** (no abortar) y registrar el fallo. | Alta |
| RF-08 | Debe aplicar una **pausa** (≈ 2 s) entre búsquedas para no saturar las fuentes. | Media |
| RF-09 | Debe permitir ampliar la lista de fuentes sin reescribir el pipeline (fuente = módulo que devuelve dicts crudos con el mismo contrato). | Media |

**RF-10 (NUEVO — Fuentes adicionales):** El sistema debe soportar un **conector de fuentes secundarias** con estas variantes:

| ID | Fuente | Descripción | Método |
|---|---|---|---|
| RF-10a | **Google Jobs / agrupadores** | Búsqueda agregada por URLs públicas | Scraping read-only |
| RF-10b | **Remotive / We Work Remotely / Ofertas Data** | Tablones orientados a remoto y a perfiles data | API pública o scraping |
| RF-10c | **RSS de portales** (Workable, Greenhouse, Lever) | Empresas objetivo publican vía ATS | Feed RSS / URLs públicas |

> **Decisión de diseño (RF-10):** las fuentes secundarias deben convertirse al **mismo contrato de datos** que `source.py` (dicts crudos). De este modo, `transform.py`, `cache.py` y `alerts.py` **no cambian** aunque se agreguen fuentes. Se excluyen fuentes que requieran acceso autenticado o scraping de perfiles personales en redes sociales (ver §7.7): el riesgo de bloqueo de cuenta/IP supera el beneficio.

> **Opción evaluada y descartada — comentarios de reclutadores:** se evaluó capturar publicaciones/comentarios de reclutadores en su cuenta personal que contengan palabras clave del perfil (p. ej. `snowflake`, `ETL`, `Data Engineer`, `DWH`) exigiendo 2-3 coincidencias de los Planes A/B/C. Aunque es técnicamente viable mediante búsqueda por frases y heurística de coincidencias, requiere **acceso autenticado y scraping de contenido personal de LinkedIn**, lo que viola sus términos de servicio y expone la cuenta a bloqueo, captchas y posibles acciones legales. **Descartado** en favor de fuentes de bajo riesgo.

### 4.2. Transformación y enriquecimiento (TRANSFORM)

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-11 | Debe contar **coincidencias** de términos por vacante (`titulo + descripción`), soportando sinónimos con `/` (ej: `IDMC/IICS` → cuenta 1 si aparece cualquiera). | Alta |
| RF-12 | Debe **detectar idioma** (español / no español) combinando palabras típicas de avisos laborales y `langdetect`. | Alta |
| RF-13 | Debe **determinar modalidad real** (remoto / híbrido / presencial) con prioridad: ① palabras de presencial/híbrido → no remoto; ② flag `is_remote`; ③ palabras remotas; ④ default no remoto. | Alta |
| RF-14 | Debe separar la salida en dos grupos: **calificadas** (cumplen mínimo) y **rechazadas / casi califican** (Argentina, español, ≥ 1 coincidencia bajo el mínimo). | Alta |
| RF-15 | Debe **descartar descripciones que no estén en español** (perfil: búsqueda en mercado hispano). | Alta |
| RF-16 | Debe **descartar duplicados dentro de una misma corrida** por URL. | Alta |
| RF-17 | Debe enriquecer cada vacante calificada con: `plan`, `categoria`, `pais_busqueda`, `remoto`, `idioma_es`, `coincidencias`, `terminos_match`, `sitio_origen`. | Alta |
| RF-18 | Los umbrales (`MIN_MATCHES_POR_CATEGORIA`) y los términos deben ser **configurables sin tocar código** (`config.py` / variables de entorno). | Alta |
| RF-19 | **Evolución:** la modalidad detectada debe devolver un valor **categorizado** (`remoto` / `hibrido` / `presencial`) y no solo booleano, para métricas. | Media |

### 4.3. Clasificación por Planes (perfiles de búsqueda)

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-20 | Cada categoría se asocia a un **Plan** de búsqueda (actual: A=IDMC, B=Soporte, C=ETL, D=QA). | Alta |
| RF-21 | Cada plan define sus **países objetivo** y si exige **remoto** (actual: IDMC cubre Argentina + LATAM/España con remoto; el resto solo Argentina). | Alta |
| RF-22 | La lógica de clasificación debe ser **declarativa** (config + reglas simples), permitiendo agregar un plan nuevo sin duplicar código. | Media |
| RF-23 | El email debe mostrar el **conteo por plan** para priorizar la lectura. | Media |

### 4.4. Deduplicación y estado (CACHE / ESTADO)

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-24 | Debe persistir un registro de URLs ya notificadas (`vacantes_vistas.json`) para no reenviar vacantes conocidas. | Alta |
| RF-25 | Debe guardar `ultima_actualizacion`, `total_urls` y la lista de URLs, con codificación UTF-8. | Alta |
| RF-26 | **Evolución:** además de URLs, debe almacenar **metadata por vacante** (fecha detectada, plan, fuente, estado de postulación) en un esquema estable (JSONL o SQLite) para alimentar métricas. | Media |
| RF-27 | **Evolución:** se debe ofrecer una **ventana de retención** (ej: descartar URLs con más de 90 días) para evitar que el archivo crezca indefinidamente. | Media |
| RF-28 | El archivo de estado debe tolerar corrupción (leer vacío y no romper la corrida). | Alta |

### 4.5. Notificaciones (LOAD)

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-29 | Debe construir un **email HTML** con tabla de vacantes (Plan, Título enlazado, Empresa, Ubicación, Modalidad, Categoría, Coincidencias, Fuente). | Alta |
| RF-30 | Debe generar un **email separado para "casi califican"** (Argentina) con estilo diferenciado. | Media |
| RF-31 | Debe enviar vía **Gmail SMTP** (`smtp.gmail.com:587`, STARTTLS, app password). | Alta |
| RF-32 | El asunto debe incluir el **número de vacantes** entre paréntesis. | Media |
| RF-33 | Si no hay vacantes nuevas, el email debe decir que no se encontraron (mensaje vacío, sin errores). | Media |
| RF-34 | **Evolución:** la salida debe ser **intercambiable** (Email / Slack / Telegram) mediante una interfaz de notificador; el cambio no debe afectar al resto del pipeline. | Media |
| RF-35 | **Evolución:** si `DEBUG=True`, debe imprimir en consola el detalle de cada decisión (descartado, duplicado, calificado). | Media |

### 4.6. Programación y ejecución

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-36 | Modo **manual**: `python main.py --once` ejecuta una corrida y termina. | Alta |
| RF-37 | Modo **programado**: ejecuta automáticamente a los horarios configurados (`HORARIOS_EJECUCION`, actual 10:00 / 15:00 / 17:00). | Alta |
| RF-38 | El proceso debe quedar **ligero** (loop con `schedule` y sleep de 30 s). | Media |
| RF-39 | **Evolución:** debe soportar un **flag de planos** (`--plans A C`) para ejecutar solo las categorías deseadas. | Media |
| RF-40 | **Evolución:** debe registrar un **log de corridas** (timestamp, resultados por categoría, errores) para auditoría. | Media |

### 4.7. Configuración

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-41 | Credenciales sensibles (email, app password) en **variables de entorno** (`.env`), nunca en el código. | Alta |
| RF-42 | Términos, umbrales, horarios, países y keywords en `config.py` como **datos declarativos**. | Alta |
| RF-43 | No deben incluirse secretos en el control de versiones (`.gitignore`). | Alta |

---

## 5. Requerimientos no funcionales

| ID | Requerimiento | Prioridad |
|---|---|---|
| RNF-01 | **Modularidad:** separación estricta ETL (`source` / `transform` / `cache` / `alerts` / `pipeline` / `main`). Un módulo no conoce los detalles internos de otro. | Alta |
| RNF-02 | **Mantenibilidad:** cada módulo tiene responsabilidad única y puede probarse de forma aislada (`python <modulo>.py` con datos de ejemplo). | Alta |
| RNF-03 | **Escalabilidad horizontal:** agregar categorías/fuentes no requiere cambios en `pipeline.py`. | Media |
| RNF-04 | **Rendimiento:** una corrida completa debe completarse en < 5 min con ~25 resultados por búsqueda. | Media |
| RNF-05 | **Robustez:** una falla en una fuente/categoría no debe interrumpir el resto de la corrida. | Alta |
| RNF-06 | **Portabilidad:** Python 3.10+, dependencias listadas en `requirements.txt`; funcionar en Windows/Linux. | Media |
| RNF-07 | **Observabilidad:** logs claros en consola con el detalle de cada paso y conteos. | Media |
| RNF-08 | **Seguridad:** credenciales fuera del código; email de aplicación de Gmail (no contraseña principal). | Alta |
| RNF-09 | **Confiabilidad del estado:** la deduplicación debe ser **idempotente** (correr dos veces seguidas no produce segundos envíos). | Alta |

---

## 6. Arquitectura técnica

### 6.1. Diagrama de la v1 (línea base)

```
 proyecto/
 ├── config.py        # Credenciales, términos, umbrales, horarios, países
 ├── source.py        # EXTRACT: llama a JobSpy (LinkedIn + Indeed)
 ├── transform.py     # TRANSFORM: relevancia, idioma, modalidad, Plan
 ├── cache.py         # ESTADO: lectura/escritura de vacantes_vistas.json
 ├── alerts.py        # LOAD: HTML + envío por Gmail SMTP
 ├── pipeline.py      # Orquestador: orden de la corrida
 ├── main.py          # Entrada: manual (--once) o programado (schedule)
 └── Data/
     └── vacantes_vistas.json
```

### 6.2. Flujo de una corrida

```
 main (manual / schedule)
   └── pipeline.ejecutar_corrida()
         1. cargar_vistos()                     (cache.py)
         2. por categoría en TERMINOS:
               source.extraer_jobs_categoria()   → dicts crudos   [EXTRACT]
               transform.transformar_categoria() → calificadas + rechazadas  [TRANSFORM]
         3. filtrar nuevas (URL no vista)        (cache.py)
         4. construir_html() + enviar_email()    (alerts.py)      [LOAD]
         5. guardar_vistos()                     (cache.py)       [ESTADO]
```

### 6.3. Arquitectura objetivo (evolución propuesta)

Se mantiene el patrón ETL modular y se agregan **conectores de fuente** y **almacén de historial** sin acoplar módulos:

```
                    ┌─────────────── FUENTES (EXTRACT) ───────────────┐
                    │  [JobSpy] LinkedIn + Indeed   (v1, activo)      │
                    │  [SourceJobsBoards] Remotive/WWR/RSS/Google Jobs│
                    └───────────────┬────────────────────────────────┘
                                   ▼ contrato: lista[dict] crudos
                    ┌─────────────── TRANSFORM ────────────────────────┐
                    │  relevancia (matches) · idioma · modalidad      │
                    │  clasificación Plan A/B/C/D · normalización     │
                    └───────────────┬────────────────────────────────┘
                                   ▼ calificadas + rechazadas
                    ┌─────────────── ESTADO / HISTORIAL ───────────────┐
                    │  vacantes_vistas.json  (dedup, v1)               │
                    │  historial.sqlite/jsonl  (métricas, v2)          │
                    └───────────────┬────────────────────────────────┘
                                   ▼ nuevas
                    ┌─────────────── LOAD / NOTIFICACIÓN ──────────────┐
                    │  Email (Gmail SMTP) · (futuro) Slack/Telegram    │
                    └───────────────┬────────────────────────────────┘
                                   ▼
                         Usuario (Data Engineer)
```

### 6.4. Contrato de datos (interfaz entre módulos)

**Dict "crudo" (salida de `source.py` y futuros conectores):**

```python
{
  "categoria": str,          # "IDMC" | "ETL" | ...
  "pais_busqueda": str,      # país usado en la búsqueda
  "requiere_remoto": bool,
  "titulo": str,
  "empresa": str,
  "ubicacion": str,
  "descripcion": str,
  "url": str,                # clave de deduplicación
  "is_remote_flag": bool|None,
  "sitio_origen": str,       # linkedin | indeed | remotive | rss | ...
}
```

**Dict "calificada" (salida de `transform.py`):**

```python
{
  "plan": str,               # A | B | C | D
  "categoria": str,
  "pais_busqueda": str,
  "titulo": str,
  "empresa": str,
  "ubicacion": str,
  "remoto": bool,            # (v2: "remoto"|"hibrido"|"presencial")
  "idioma_es": bool,
  "coincidencias": int,
  "terminos_match": str,     # términos que matchearon
  "sitio_origen": str,
  "url": str,
}
```

> **Regla de oro:** los conectores de fuente deben devolver **dicts crudos con el mismo esquema**. `transform.py`, `cache.py` y `alerts.py` NO se modifican al agregar fuentes.

---

## 7. Reglas de negocio detalladas

### 7.1. Filtrado por relevancia

- Se concatenan `titulo + descripción` y se cuentan cuántos términos de la categoría aparecen (`contar_coincidencias`).
- Términos con `/` (sinónimos) cuentan **1 coincidencia** si aparece cualquiera de las partes.
- Umbrales actuales (`MIN_MATCHES_POR_CATEGORIA`): IDMC=1, SOPORT=3, ETL=2, QA=2.

### 7.2. Detección de idioma

- Si la descripción tiene menos de 50 caracteres → se considera **no español** (insuficiente).
- Español si: contiene palabras típicas de avisos (`beneficios`, `vacante`, `experiencia`, `postularse`, …) **o** `langdetect` devuelve `es`.
- Cubre el caso de título en inglés ("Data Engineer") con descripción en español.

### 7.3. Modalidad

Orden de evaluación (primera que aplica, gana):

1. Contiene keyword de híbrido/presencial (`híbrido`, `hybrid`, `presencial`, `on-site`, …) → **no remoto** (aunque `is_remote=True`).
2. `is_remote_flag is True` (dato de JobSpy) → **remoto**.
3. Contiene keyword remota (`remote`, `remoto`, `work from home`, `open to latam`, …) → **remoto**.
4. Caso contrario → **no remoto**.

### 7.4. Clasificación por Plan

| Plan | Categoría | Países | Remoto |
|---|---|---|---|
| **A** | IDMC / Informatica Cloud | Argentina + LATAM (Chile, Perú, México, Colombia, Uruguay, Costa Rica, España, Venezuela, Ecuador, Panamá, Worldwide) | opcional según vacante |
| **B** | Soporte de datos | Argentina | no exigido |
| **C** | ETL / Data Engineer | Argentina | no exigido |
| **D** | QA / Calidad de datos | Argentina | no exigido |

### 7.5. "Casi califican" (rechazadas)

Se capturan como candidatas a revisión manual solo si cumplen **todas**:
1. País de búsqueda = **Argentina**.
2. Al menos **2 coincidencias**.
3. Descripción en **español**.

No llegan al umbral de su categoría, pero merecen revisión.

### 7.6. Deduplicación

- Clave = **URL** de la vacante.
- Al finalizar la corrida se guardan TODAS las URLs procesadas (calificadas y rechazadas) para no volver a notificarlas.
- Dentro de una misma corrida se descartan URLs ya procesadas por otra categoría.

### 7.7. Exclusión de fuentes de alto riesgo (comentarios de reclutadores)

Se evaluó capturar publicaciones/comentarios de reclutadores en su **cuenta personal de LinkedIn** que contengan palabras clave del perfil (p. ej. `snowflake`, `ETL`, `Data Engineer`, `DWH`), exigiendo **2-3 coincidencias** de los Planes A/B/C y procesándolas con las mismas reglas de `transform.py`.

**Motivos de descarte (riesgo/beneficio desfavorable):**
- **ToS de LinkedIn:** el scraping de contenido personal (publicaciones, comentarios, perfiles) está explícitamente prohibido; no es comparable a consultar listados públicos de empleo.
- **Riesgo de bloqueo:** requiere sesión autenticada y navegación automatizada sobre contenido de usuarios → riesgo alto de banneo de cuenta, captchas y bloqueo de IP.
- **Calidad:** contenido no estructurado con alta tasa de falsos positivos, sin esquema estable.
- **Alternativa segura:** los mismos leads (vacantes de reclutadores) aparecen mayormente ya publicados como **listados de empleo** en LinkedIn/Indeed, que sí cubren JobSpy y las fuentes secundarias de bajo riesgo.

**Decisión:** el sistema **no** incorpora esta fuente. Queda documentado como caso analizado y descartado por decisión de riesgo.

---

## 8. Modelo de datos (evolución)

### 8.1. `Data/vacantes_vistas.json` (v1)

```json
{
  "ultima_actualizacion": "2026-08-12T10:00:00",
  "total_urls": 1234,
  "urls": ["https://...", "..."]
}
```

### 8.2. `historial` propuesto (v2, para métricas)

| Campo | Tipo | Descripción |
|---|---|---|
| `url` | TEXT (PK) | Clave de dedup |
| `plan` | TEXT | A/B/C/D |
| `categoria` | TEXT | IDMC / ETL / … |
| `fuente` | TEXT | linkedin / indeed / remotive / rss / … |
| `titulo` | TEXT | Normalizado |
| `empresa` | TEXT | — |
| `ubicacion` | TEXT | — |
| `modalidad` | TEXT | remoto / hibrido / presencial |
| `idioma_es` | INT | 0/1 |
| `coincidencias` | INT | Matches |
| `fecha_detectada` | TEXT (ISO) | Timestamp de la corrida |
| `estado` | TEXT | detectada / postulada / descartada |

**Fuente primaria sugerida:** SQLite (un archivo, sin servidor, consultable). Alternativa JSONL para simplicidad.

---

## 9. Decisiones de diseño (arquitectura y por qué)

| Decisión | Alternativa descartada | Justificación |
|---|---|---|
| **Patrón ETL modular (módulos separados)** | Monolito con funciones mezcladas | Cada pieza es testeable, reemplazable y leíble; el orquestador solo conoce el orden. |
| **Deduplicación por URL** | Dedup por título/empresa | La URL es estable y única; evita falsos duplicados entre títulos similares. |
| **Detección de idioma combinada** (keywords + langdetect) | Solo `langdetect` | Evita falsos negativos con descripciones cortas o técnicas mixtas EN/ES. |
| **Modalidad con reglas de prioridad** | Confiar en `is_remote` de la fuente | El flag de la fuente es poco fiable; el texto corrige falsos "remoto". |
| **Clasificación declarativa por config** | Clasificador hardcodeado | Agregar/quitar planes = editar datos, no lógica. |
| **Conectores de fuente con contrato común** | Funciones específicas por fuente | Escala a nuevas fuentes (tablones, RSS) sin tocar transform/alertas. |
| **Email HTML simple por SMTP** | Servicio de email externo | Cero costos, cero dependencias externas; suficiente para un usuario. |
| **Estado en JSON con tolerancia a corrupción** | Base de datos en v1 | Simplicidad; migra a SQLite en v2 sin cambiar la interfaz (`cargar_vistos`/`guardar_vistos`). |
| **Horarios fijos con `schedule`** | Cron del SO / cola de tareas | Portable y simple; suficiente mientras la PC esté encendida. |
| **No postulación automática (v1)** | Bot que aplica solo | Riesgo legal/ToS y reputacional; v1 informa, v2+ puede sugerir y automatizar con consentimiento. |

---

## 10. Evolución respecto al modelo v1 (resumen de cambios)

| Tema | Modelo v1 (base) | Evolución especificada |
|---|---|---|
| Fuentes | LinkedIn + Indeed (JobSpy) | + Tablones remotos, RSS/ATS, Google Jobs (excluye redes sociales por riesgo ToS) |
| Modalidad | Booleano (`remoto` sí/no) | Categoría `remoto/hibrido/presencial` |
| Estado | Solo URLs en JSON | + Historial con metadata y métricas (SQLite/JSONL) |
| Métricas | Ninguna | Dashboard/exporte: vacantes por semana/plan/fuente, postulaciones |
| Notificación | Email | Interfaz intercambiable (Email + Slack/Telegram futuro) |
| Auditoría | Logs de consola | Log de corridas persistente |
| Retención | Sin límite | Ventana de retención de URLs (90 días) |
| Ejecución | `--once` y horarios fijos | + `--plans` (correr categorías seleccionadas) |

---

## 11. Roadmap propuesto

| Fase | Entregables | Estado |
|---|---|---|
| **F1 (v1, existente)** | JobSpy LinkedIn+Indeed, planes A/B/C/D, email, dedup, schedule | ✅ Implementado |
| **F2** | Modalidad categorizada, log de corridas, flag `--plans`, historial SQLite + métricas | 🔜 En diseño |
| **F3** | Conector de tablones remotos (Remotive/WWR), agregadores y RSS de ATS | 🔜 En diseño |
| **F4** | Dashboard (Streamlit/Gradio) con métricas de postulación | 💡 Futuro |
| **F5** | Notificador Slack/Telegram; sugerencia de postulación semiautomática | 💡 Futuro |

---

## 12. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Scraping prohibido por ToS (LinkedIn) | Alto | Límites de frecuencia; vía curada/manual; leer ToS por fuente; alternativas con API. |
| Bloqueo / captcha de fuentes | Medio | Pausas, `hours_old`, degradación con gracia, rotación de IPs (no recomendado). |
| Falsos positivos en relevancia | Medio | Umbrales por categoría; revisión de "casi califican". |
| Pérdida/corrupción del archivo de estado | Medio | Tolerancia a corrupción; backup de `vacantes_vistas.json`; migración a SQLite. |
| PC apagada en horarios fijos | Medio | Documentar; alternativa: ejecutar desde GitHub Actions/Cloud Scheduler (v3). |
| Credenciales expuestas | Alto | `.env` + `.gitignore`; app password; nunca en el repo. |

---

## 13. Métricas de éxito del producto

1. **Cobertura de fuentes:** ≥ 2 fuentes activas en v1, ≥ 4 en v3.
2. **Precisión de relevancia:** > 70 % de las vacantes notificadas resultan postulables.
3. **Latencia de alerta:** < 24 h desde la publicación.
4. **Carga manual eliminada:** 0 interacciones manuales por corrida (excepto postulación).
5. **Falsos duplicados:** 0 reenvíos de la misma URL.

---

## 14. Anexos

### A. Requisitos de entorno (v1)

```bash
pip install python-jobspy langdetect pandas schedule python-dotenv
```

### B. Configuración crítica

- Gmail: activar verificación en 2 pasos y generar **app password** (16 caracteres).
- `.env`: `EMAIL_REMITENTE`, `EMAIL_APP_PASSWORD` (y opcionalmente `EMAIL_DESTINATARIO`).
- `config.py`: `TERMINOS`, `MIN_MATCHES_POR_CATEGORIA`, `PLANES_PAISES`, `HORARIOS_EJECUCION`, `REMOTE_KEYWORDS`, `HYBRID_KEYWORDS`.

### C. Comandos

```bash
python main.py --once    # corrida manual
python main.py           # modo programado (10:00 / 15:00 / 17:00)
python source.py         # prueba aislada de extracción
python transform.py      # prueba aislada de transformación
```

### D. Glosario

| Término | Definición |
|---|---|
| **Corrida** | Ejecución completa del pipeline (extract → transform → notificar → estado). |
| **Categoría** | Agrupación de términos de búsqueda (IDMC, SOPORT, ETL, QA). |
| **Plan** | Perfil de búsqueda priorizado asociado a una categoría (A/B/C/D). |
| **Calificada** | Vacante que cumple el mínimo de coincidencias de su categoría y está en español. |
| **Rechazada / casi califica** | Vacante de Argentina, en español, con ≥ 2 coincidencias pero bajo el mínimo. |
| **Modalidad** | remoto / híbrido / presencial, inferida por reglas y datos de la fuente. |
