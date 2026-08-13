"""
main.py
=======
Punto de entrada del programa.

Uso:

    Modo manual (una sola corrida):
        python main.py --once

    Solo ciertos Planes (A/C/D):
        python main.py --once --plans A C

    Modo programado (corre en HORARIOS_EJECUCION):
        python main.py
"""
import argparse
import time

import schedule

from config import HORARIOS_EJECUCION, CATEGORIA_A_PLAN
from pipeline import ejecutar_corrida
from logging_config import setup_logging


def validar_planes(planes):
    """Devuelve la lista de Planes válidos (A/B/C/D) o None = todos."""
    if not planes:
        return None
    validos = set(CATEGORIA_A_PLAN.values())
    planes_norm = [p.upper() for p in planes]
    invalidos = set(planes_norm) - validos
    if invalidos:
        print(f"[!] Planes inválidos ignorados: {sorted(invalidos)}. Válidos: {sorted(validos)}")
    return [p for p in planes_norm if p in validos] or None


def modo_programado():
    print("[BOT] Bot de vacantes iniciado en modo PROGRAMADO")
    print(f"[HORARIOS] Horarios de ejecución: {', '.join(HORARIOS_EJECUCION)}")
    print("[STOP] Para detener: Ctrl + C\n")
    print("Dejá esta ventana abierta. El script se ejecutará automáticamente")
    print("en los horarios configurados, sin que tengas que hacer nada más.\n")

    for hora in HORARIOS_EJECUCION:
        schedule.every().day.at(hora).do(ejecutar_corrida)

    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(
        description="Bot de búsqueda de vacantes para perfil Data Engineer"
    )
    parser.add_argument("--once", action="store_true",
                        help="Ejecuta una sola corrida y termina")
    parser.add_argument("--plans", nargs="*", default=None,
                        help="Solo estos Planes (ej: A C D). Sin flag = todos")
    parser.add_argument("--reenviar", action="store_true",
                        help="Envía email con los resultados ya guardados "
                             "en el historial (sin re-scrapear)")
    args = parser.parse_args()

    setup_logging()

    if args.reenviar:
        from pipeline import reenviar_resultado

        reenviar_resultado()
        return

    planes = validar_planes(args.plans)
    if planes:
        print(f"[PLANES] Planes activos para esta corrida: {', '.join(planes)}")

    if args.once:
        ejecutar_corrida(planes=planes)
    else:
        modo_programado()


if __name__ == "__main__":
    main()
