"""
Archivo: normalizar_simulacro.py
Ruta: core/normalizar_simulacro.py

Convierte el JSON de un simulacro en el modelo interno.
"""

import json
from pathlib import Path

from core.modelo_simulacro import (
    Simulacro,
    Pregunta,
    Opcion,
)


def cargar_simulacro(
    ruta,
):

    ruta = Path(ruta)

    datos = json.loads(
        ruta.read_text(
            encoding="utf-8"
        )
    )

    simulacro = Simulacro(
        completo=datos.get(
            "completo",
            False,
        ),
        preguntas_ia=datos.get(
            "preguntas_ia",
            0,
        ),
    )

    for p in datos["preguntas"]:

        opciones = []

        for letra in (
            "A",
            "B",
            "C",
            "D",
        ):

            opciones.append(
                Opcion(
                    letra=letra,
                    texto=p["opciones"][letra],
                )
            )

        simulacro.preguntas.append(

        Pregunta(

            numero=p["numero_simulacro"],

            enunciado=p["enunciado"],

            opciones=opciones,

            respuesta_correcta=p["respuesta_correcta"],

            texto_respuesta_correcta=p.get(
                "texto_respuesta_correcta"
            ),

            tipo_pregunta=p["tipo_pregunta"],

            tema=p.get("tema"),

            norma=p.get("norma"),

            articulo=p.get("articulo"),

            origen=p.get(
                "origen",
                "BANCO",
            ),

            fragmento=p.get(
                "fragmento"
            ),

            explicacion=p.get(
                "explicacion"
            ),
        )
        )

    return simulacro