"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : normalizar_simulacro.py
Ruta    : core/normalizar_simulacro.py

Objetivo:
    Convertir un JSON de simulacro al modelo interno de renderizado.

Entradas:
    - Ruta de un JSON de simulacro.

Salidas:
    - Objeto Simulacro normalizado.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.modelo_simulacro

Utilizado por:
    - procesos/generar_pdf.py

Flujo:
    1. Lee el JSON.
    2. Valida campos.
    3. Construye opciones y preguntas.

Observaciones:
    - Ninguna.

==============================================================================
"""
import json
from pathlib import Path

from core.modelo_simulacro import (
    Simulacro,
    Pregunta,
    Opcion,
)

def normalizar_datos_simulacro(
    datos: dict,
) -> Simulacro:

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

        opciones = [
            Opcion(
                letra=letra,
                texto=p["opciones"][letra],
            )
            for letra in (
                "A",
                "B",
                "C",
                "D",
            )
        ]

        simulacro.preguntas.append(
            Pregunta(
                numero=p["numero_simulacro"],
                enunciado=p["enunciado"],
                opciones=opciones,
                respuesta_correcta=p[
                    "respuesta_correcta"
                ],
                texto_respuesta_correcta=p.get(
                    "texto_respuesta_correcta"
                ),
                tipo_pregunta=p[
                    "tipo_pregunta"
                ],
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


def cargar_simulacro(ruta):

    ruta = Path(ruta)

    datos = json.loads(
        ruta.read_text(
            encoding="utf-8"
        )
    )

    return normalizar_datos_simulacro(
        datos
    )

