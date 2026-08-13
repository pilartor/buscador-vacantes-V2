"""
Conector: feeds RSS / feeds XML públicos.

Cubre feeds de tablones (Remotive), blogs de ATS y cualquier fuente que
exponga un feed público. Mismo contrato de datos que el resto de fuentes.
"""
import time

from config import RSS_FEEDS, PAUSA_ENTRE_BUSQUEDAS
from sources.base import crudo, es_url_valida


def _fecha(item):
    """Extrae un timestamp legible de la entrada (o vacío)."""
    ts = item.get("published_parsed") or item.get("updated_parsed")
    if ts:
        import calendar
        from datetime import datetime, timezone

        return datetime.fromtimestamp(calendar.timegm(ts), tz=timezone.utc).isoformat()
    return ""


def extraer(categoria):
    import feedparser  # import perezoso

    crudos = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"   [!] [rss] Error parseando {feed_url}: {e}")
            continue

        for item in feed.entries or []:
            link = str(item.get("link", "") or "").strip()
            if not es_url_valida(link):
                continue
            crudos.append(
                crudo(
                    categoria=categoria,
                    titulo=item.get("title", ""),
                    empresa=item.get("company", "") or item.get("publisher", ""),
                    ubicacion=item.get("location", "") or "Worldwide",
                    descripcion=item.get("summary", "") or item.get("description", ""),
                    url=link,
                    sitio_origen="rss",
                    pais_busqueda="Worldwide",
                )
            )
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return crudos
