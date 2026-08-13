"""
transform.py
============
Capa TRANSFORM del pipeline.

Responsabilidad ÚNICA de este archivo:
    - Recibir vacantes "crudas" (contrato de sources/base.py)
    - Filtrar por relevancia (coincidencias con los términos)
    - Detectar idioma (español / no español)
    - Detectar modalidad REAL: "remoto" | "hibrido" | "presencial"
    - Clasificar en Plan (A/B/C/D) según la categoría
    - Separar en:
        * "calificadas"  -> cumplen el mínimo de coincidencias
        * "rechazadas"   -> >= 1 coincidencia pero bajo el mínimo
                            (solo Argentina, en español -> "casi califican")

NO hace scraping (eso es source.py) y NO notifica ni guarda archivos
(eso es alerts.py / cache.py / history.py).
"""
from datetime import datetime

from langdetect import detect, LangDetectException

from config import (
    TERMINOS,
    MIN_MATCHES_POR_CATEGORIA,
    CATEGORIA_A_PLAN,
    REMOTE_KEYWORDS,
    HYBRID_KEYWORDS,
    PRESENCIAL_KEYWORDS,
    DEBUG,
    KEYWORDS_PESO,
    SENALES_ROL,
    PESO_SENAL_ROL,
    SENALES_NEGATIVAS,
    PENALIDAD_NEGATIVA,
    UMBRAL_SCORE,
)


# ─────────────────────────────────────────────
def contar_coincidencias(texto, terminos):
    """
    Cuenta cuántos términos de `terminos` aparecen en `texto`.

    Soporta términos con "/" como sinónimos (ej "IDMC/IICS"):
    si aparece CUALQUIERA de las partes, cuenta como 1 coincidencia.

    Devuelve (hits, matched).
    """
    texto_l = texto.lower()
    hits = 0
    matched = []

    for t in terminos:
        if "/" in t:
            partes = t.lower().split("/")
            if any(p.strip() in texto_l for p in partes if p.strip()):
                hits += 1
                matched.append(t)
        else:
            if t.lower() in texto_l:
                hits += 1
                matched.append(t)

    return hits, matched


# ─────────────────────────────────────────────
def es_espanol(texto):
    """
    Determina si una descripción está en español usando dos señales:
        1. Palabras típicas de avisos laborales en español.
        2. langdetect.

    Si CUALQUIERA da positivo -> español. Cubre títulos en inglés
    ("Data Engineer") con descripción en español.
    """
    if not texto or len(str(texto).strip()) < 50:
        return False

    palabras_es = [
        "beneficios", "prestaciones", "vacante", "equipo",
        "experiencia", "postularse", "desarrollo", "cuenta", "llevamos",
    ]
    contiene_es = any(p in texto.lower() for p in palabras_es)

    try:
        es_es = detect(texto) == 'es'
    except LangDetectException:
        es_es = False

    return es_es or contiene_es


# ─────────────────────────────────────────────
def detectar_modalidad(ubicacion, descripcion, is_remote_flag):
    """
    Determina la modalidad REAL de la vacante.

    Reglas (en este orden):
        1. Keywords de presencial            -> "presencial"
        2. Keywords de híbrido               -> "hibrido"
        3. JobSpy marcó is_remote_flag=True  -> "remoto"
        4. Keywords de remoto                -> "remoto"
        5. Default                           -> "presencial"

    Las keywords de presencial/híbrido pesan más que el flag de la
    fuente (el flag es poco fiable).
    """
    texto = f"{ubicacion} {str(descripcion)[:1000]}".lower()

    if any(k in texto for k in PRESENCIAL_KEYWORDS):
        return "presencial"
    if any(k in texto for k in HYBRID_KEYWORDS):
        return "hibrido"
    if is_remote_flag is True:
        return "remoto"
    if any(k in texto for k in REMOTE_KEYWORDS):
        return "remoto"
    return "presencial"


def es_remoto_real(ubicacion, descripcion, is_remote_flag):
    """Compat: bool remoto a partir de la modalidad categorizada."""
    return detectar_modalidad(ubicacion, descripcion, is_remote_flag) == "remoto"


# ─────────────────────────────────────────────
def puntuar_rol(categoria, titulo, descripcion):
    """
    Motor de rol: puntúa el cuerpo de la vacante según el perfil del CV.

    - Suma el peso de términos clave de la categoría (KEYWORDS_PESO).
    - Suma PESO_SENAL_ROL por cada señal de rol confirmada (SENALES_ROL).
    - Resta PENALIDAD_NEGATIVA por cada señal de rol ajeno (SENALES_NEGATIVAS).

    Devuelve (score, detalle) donde detalle lista lo que sumó/restó.
    """
    texto = f"{titulo} {descripcion}".lower()
    score = 0.0
    detalle = []

    for termino, peso in KEYWORDS_PESO.get(categoria, {}).items():
        if termino in texto:
            score += peso
            detalle.append(termino)

    for senal in SENALES_ROL.get(categoria, []):
        if senal in texto:
            score += PESO_SENAL_ROL
            detalle.append(senal)

    for negativa in SENALES_NEGATIVAS:
        if negativa in texto:
            score -= PENALIDAD_NEGATIVA
            detalle.append(f"!{negativa}")

    return score, detalle


# ─────────────────────────────────────────────
def transformar_categoria(vacantes_crudas, categoria, vistos_corrida=None):
    """
    Función principal de este módulo.

    Devuelve (calificadas, rechazadas).
    """
    if vistos_corrida is None:
        vistos_corrida = set()

    terminos = TERMINOS[categoria]
    min_matches = MIN_MATCHES_POR_CATEGORIA[categoria]
    plan = CATEGORIA_A_PLAN[categoria]

    calificadas = []
    rechazadas = []

    for vacante in vacantes_crudas:
        titulo       = vacante["titulo"]
        empresa      = vacante["empresa"]
        ubicacion    = vacante["ubicacion"]
        descripcion  = vacante["descripcion"]
        url          = vacante["url"]
        pais         = vacante["pais_busqueda"]
        is_remote_flag = vacante["is_remote_flag"]
        fecha        = vacante.get("fecha_detectada") or datetime.now().isoformat(timespec="seconds")

        texto_completo = f"{titulo} {descripcion}"
        hits, matched = contar_coincidencias(texto_completo, terminos)

        # No llega al mínimo de coincidencias
        if hits < min_matches:
            if DEBUG:
                print(f"      [X] DESCARTADO ({hits} match: {matched}) -> '{titulo}'")

            # Capturar "casi califican" SOLO para Argentina y en español
            if pais == "Argentina" and hits >= 2 and es_espanol(descripcion):
                rechazadas.append({
                    "plan":            plan,
                    "categoria":       categoria,
                    "pais_busqueda":   pais,
                    "titulo":          titulo,
                    "empresa":         empresa,
                    "ubicacion":       ubicacion,
                    "coincidencias":   hits,
                    "terminos_match":  ", ".join(matched),
                    "sitio_origen":    vacante.get("sitio_origen", ""),
                    "url":             url,
                    "fecha_detectada": fecha,
                })
            continue

        # Cumple el mínimo de coincidencias
        # Motor de rol: la descripción debe confirmar el perfil de datos
        score, detalle_rol = puntuar_rol(categoria, titulo, descripcion)
        umbral = UMBRAL_SCORE.get(categoria, 0)
        if score < umbral:
            if DEBUG:
                print(f"      [X] NO ES ROL ({score:.0f}<{umbral}: {detalle_rol[:6]}) -> '{titulo}'")
            continue

        idioma_es = es_espanol(descripcion)

        # Descartar si la descripción NO está en español
        if not idioma_es:
            continue

        modalidad = detectar_modalidad(ubicacion, descripcion, is_remote_flag)

        if url in vistos_corrida:
            if DEBUG:
                print(f"      [X] DUPLICADO EN CORRIDA -> '{titulo}'")
            continue

        calificadas.append({
            "plan":            plan,
            "categoria":       categoria,
            "pais_busqueda":   pais,
            "titulo":          titulo,
            "empresa":         empresa,
            "ubicacion":       ubicacion,
            "modalidad":       modalidad,
            "remoto":          modalidad == "remoto",
            "idioma_es":       idioma_es,
            "coincidencias":   hits,
            "terminos_match":  ", ".join(matched),
            "score_rol":       score,
            "sitio_origen":    vacante.get("sitio_origen", ""),
            "url":             url,
            "fecha_detectada": fecha,
        })

    return calificadas, rechazadas


# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Prueba rápida aislada con datos de ejemplo (sin red, sin email)
    ejemplo = [
        {
            "categoria": "ETL", "pais_busqueda": "Argentina",
            "requiere_remoto": False, "titulo": "Data Engineer - Snowflake",
            "empresa": "Empresa X", "ubicacion": "Buenos Aires, Argentina",
            "descripcion": "Buscamos Data Engineer con experiencia en ETL, "
                           "Snowflake y pipelines de datos. Beneficios, "
                           "modalidad híbrida, postularse vía página.",
            "url": "https://example.com/1", "is_remote_flag": False,
            "sitio_origen": "linkedin",
        },
    ]
    calificadas, rechazadas = transformar_categoria(ejemplo, "ETL")
    print(f"Calificadas: {len(calificadas)} | Rechazadas: {len(rechazadas)}")
    if calificadas:
        print(calificadas[0])
