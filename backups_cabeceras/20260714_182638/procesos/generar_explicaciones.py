"""
Archivo: generar_explicaciones.py
Ruta: procesos/generar_explicaciones.py

Genera explicaciones para un simulacro.

Si una explicación ya existe en la BD, la reutiliza.
Si no existe, la genera mediante IA.

Al finalizar crea:

simulacro_xxx_explicado.json
"""

import json
from pathlib import Path

from core.buscar_explicacion import buscar_explicacion
from core.construir_prompt_explicacion import construir_prompt
from core.guardar_explicacion import guardar_explicacion
from core.huellas import calcular_huella
from core.obtener_fragmento import obtener_fragmento
from core.openai_api import generar_explicacion_ia


def enriquecer_simulacro(
    ruta_json,
    modelo="gpt-5.4-mini",
):

    ruta_json = Path(ruta_json)

    simulacro = json.loads(
        ruta_json.read_text(
            encoding="utf-8"
        )
    )

    reutilizadas = 0
    generadas = 0

    for pregunta in simulacro["preguntas"]:

        huella = calcular_huella(
            pregunta["enunciado"],
            pregunta["opciones"],
        )

        existente = buscar_explicacion(
            huella
        )

        if existente:

            pregunta["explicacion"] = existente

            reutilizadas += 1

            continue

        fragmento = obtener_fragmento(
            pregunta.get(
                "fragmento_id"
            )
        )

        if fragmento is not None:

            pregunta["fragmento"] = fragmento

        if fragmento is None:

            pregunta["fragmento"] = None

            pregunta["explicacion"] = {
                "breve": pregunta.get(
                    "justificacion",
                    "Explicación pendiente.",
                ),
                "extensa": "",
            }

            continue

        prompt = construir_prompt(
            pregunta,
            fragmento,
        )

        respuesta = generar_explicacion_ia(
            prompt=prompt,
            modelo=modelo,
        )

        guardar_explicacion(

            pregunta_importada_id=(
            pregunta.get("id")
            if isinstance(
                pregunta.get("id"),
                int,
            )
            else None
            ),

            huella=huella,

            breve=respuesta["breve"],

            extensa=respuesta["extensa"],

            modelo=modelo,

        )

        pregunta["explicacion"] = respuesta

        generadas += 1

    salida = ruta_json.with_name(

        ruta_json.stem
        + "_explicado.json"

    )

    salida.write_text(

        json.dumps(

            simulacro,

            ensure_ascii=False,

            indent=4,

        ),

        encoding="utf-8",

    )

    print()
    print("=" * 70)
    print("EXPLICACIONES")
    print("=" * 70)
    print(f"Reutilizadas.... {reutilizadas}")
    print(f"Generadas IA.... {generadas}")
    print(f"Archivo......... {salida}")

    return salida


def main():

    carpeta = Path(
        "simulacros"
    )

    ruta = max(

        carpeta.glob(
            "*_completo.json"
        ),

        key=lambda p:
            p.stat().st_mtime,

    )

    enriquecer_simulacro(
        ruta
    )


if __name__ == "__main__":

    main()