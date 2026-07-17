"""
Archivo: generar_simulacro.py
Ruta: procesos/generar_simulacro.py

Genera un simulacro desde el banco y lo guarda en JSON.

No utiliza IA.
"""

import json
from datetime import datetime
from pathlib import Path

from core.constructor_simulacro import (
    construir_simulacro,
)


ROOT = Path(__file__).resolve().parents[1]

RUTA_SALIDA = ROOT / "simulacros"


def crear_nombre_archivo():

    marca = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    return f"simulacro_{marca}.json"


def guardar_simulacro(
    resultado,
):

    RUTA_SALIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta = (
        RUTA_SALIDA
        / crear_nombre_archivo()
    )

    contenido = {
        "total": resultado["total"],
        "completo": resultado["completo"],
        "faltantes": resultado["faltantes"],
        "faltantes_por_tema": resultado[
            "faltantes_por_tema"
        ],
        "compensaciones": resultado.get(
            "compensaciones",
            [],
        ),
        "preguntas_ia": resultado.get(
            "preguntas_ia",
            0,
        ),
        "resumen_bloques": resultado.get(
            "resumen_bloques",
            {},
        ),
        "preguntas": resultado["simulacro"],
    }

    ruta.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return ruta


def mostrar_resumen(
    resultado,
    ruta,
):

    print()
    print("=" * 80)
    print("SIMULACRO GENERADO")
    print("=" * 80)

    print(
        f"Preguntas........: {resultado['total']}"
    )

    print(
        f"Completo.........: {resultado['completo']}"
    )

    print(
        f"Archivo..........: {ruta}"
    )

    if resultado["faltantes"]:

        print()
        print("FALTANTES")

        for dato in resultado["faltantes"]:

            destino = dato.get(
                "destino",
                (
                    "IA"
                    if dato["tipo_pregunta"]
                    == "ESPECIAL_INFORMATICA"
                    else "ERROR_BANCO"
                ),
            )

            print(
                f"{dato['tipo_pregunta']:24s} "
                f"Faltan {dato['faltan']} "
                f"-> {destino}"
            )

    faltantes_por_tema = resultado.get(
        "faltantes_por_tema",
        [],
    )

    faltantes_informatica = [
        dato
        for dato in faltantes_por_tema
        if dato["tipo_pregunta"]
        == "ESPECIAL_INFORMATICA"
    ]

    if faltantes_informatica:

        print()
        print("FALTANTES DE INFORMÁTICA POR TEMA")

        for dato in faltantes_informatica:

            print(
                f"Tema {dato['tema']:>2} "
                f"Faltan {dato['faltan']}"
            )


def main():

    resultado = construir_simulacro()

    ruta = guardar_simulacro(
        resultado
    )

    mostrar_resumen(
        resultado=resultado,
        ruta=ruta,
    )


if __name__ == "__main__":

    main()