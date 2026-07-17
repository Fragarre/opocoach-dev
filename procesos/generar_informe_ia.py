"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso

Archivo : generar_informe_ia.py
Ruta    : procesos/generar_informe_ia.py

Objetivo:
    Generar el análisis IA del intento del opositor.

==============================================================================
"""

import json
from collections import Counter

from core.openai_api import (
    seleccionar_fragmento_json,
)


def _clave_texto(valor):

    if valor is None:
        return ""

    return str(valor).strip()


def _seleccionar_preguntas_representativas(
    preguntas_no_acertadas,
):

    total_errores = len(
        preguntas_no_acertadas
    )

    if total_errores <= 10:
        limite = total_errores

    elif total_errores <= 25:
        limite = 12

    else:
        limite = 15

    seleccionadas = []
    claves_usadas = set()

    for pregunta in preguntas_no_acertadas:

        clave = (
            _clave_texto(
                pregunta["tema"]
            ),
            _clave_texto(
                pregunta["norma"]
            ),
        )

        if clave in claves_usadas:
            continue

        seleccionadas.append(
            pregunta
        )

        claves_usadas.add(
            clave
        )

        if len(seleccionadas) >= limite:
            return seleccionadas

    numeros_seleccionados = {
        pregunta["numero"]
        for pregunta in seleccionadas
    }

    for pregunta in preguntas_no_acertadas:

        if (
            pregunta["numero"]
            in numeros_seleccionados
        ):
            continue

        seleccionadas.append(
            pregunta
        )

        if len(seleccionadas) >= limite:
            break

    return seleccionadas


def _construir_resumen_estadistico(
    preguntas_no_acertadas,
):

    errores_por_tema = Counter()
    errores_por_norma = Counter()
    errores_por_articulo = Counter()
    blancos = 0

    for pregunta in preguntas_no_acertadas:

        tema = _clave_texto(
            pregunta["tema"]
        )

        norma = _clave_texto(
            pregunta["norma"]
        )

        articulo = _clave_texto(
            pregunta["articulo"]
        )

        if tema:
            errores_por_tema[
                tema
            ] += 1

        if norma:
            errores_por_norma[
                norma
            ] += 1

        if norma and articulo:
            errores_por_articulo[
                f"{norma} · {articulo}"
            ] += 1

        if (
            pregunta["respuesta_usuario"]
            == "En blanco"
        ):
            blancos += 1

    return {
        "total_no_acertadas":
            len(
                preguntas_no_acertadas
            ),
        "blancos":
            blancos,
        "errores_por_tema":
            errores_por_tema.most_common(
                8
            ),
        "errores_por_norma":
            errores_por_norma.most_common(
                8
            ),
        "errores_por_referencia":
            errores_por_articulo.most_common(
                8
            ),
    }


def generar_informe_ia(
    resultado_correccion,
    modelo="gpt-5.4-mini",
):

    preguntas_no_acertadas = []

    for dato in resultado_correccion[
        "resultados_preguntas"
    ]:

        if dato["correcta"]:
            continue

        pregunta = dato["pregunta"]

        preguntas_no_acertadas.append(
            {
                "numero":
                    pregunta.numero,
                "tema":
                    pregunta.tema,
                "norma":
                    pregunta.norma,
                "articulo":
                    pregunta.articulo,
                "respuesta_usuario":
                    dato[
                        "respuesta_usuario"
                    ],
                "respuesta_correcta":
                    pregunta.respuesta_correcta,
            }
        )

    if not preguntas_no_acertadas:

        return {
            "resumen":
                "Resultado perfecto: no hay preguntas incorrectas ni en blanco.",
            "comentario_general":
                "El desempeño ha sido plenamente satisfactorio.",
            "recomendaciones": [
                "Mantén el ritmo de repaso y realiza nuevos simulacros para consolidar el nivel."
            ],
            "preguntas": [],
        }

    preguntas_representativas = (
        _seleccionar_preguntas_representativas(
            preguntas_no_acertadas
        )
    )

    resumen_estadistico = (
        _construir_resumen_estadistico(
            preguntas_no_acertadas
        )
    )

    datos_entrada = {
        "nota":
            round(
                max(
                    0,
                    resultado_correccion[
                        "nota"
                    ],
                ),
                2,
            ),
        "aciertos":
            resultado_correccion[
                "aciertos"
            ],
        "errores":
            resultado_correccion[
                "errores"
            ],
        "blancos":
            resultado_correccion[
                "blancos"
            ],
        "estadisticas":
            resumen_estadistico,
        "preguntas_representativas":
            preguntas_representativas,
    }

    prompt = f"""
Devuelve EXCLUSIVAMENTE un JSON válido.

Analiza el resultado de un opositor de la Generalitat Valenciana.

Las respuestas incorrectas penalizan un tercio de una correcta.
Las respuestas en blanco no penalizan.

Objetivo:
- detectar patrones reales de error;
- señalar debilidades por tema, norma o referencia;
- formular recomendaciones concretas y útiles;
- comentar solo las preguntas representativas incluidas.

No expliques artículos ni desarrolles contenido jurídico.
No inventes información que no figure en los datos.
No repitas la misma idea.
No recomiendes dejar preguntas en blanco de forma genérica.
Solo menciona la opción de dejar en blanco cuando, tras aplicar descarte, no exista una expectativa razonable de acierto.

Mantén un nivel de detalle útil:
- resumen: 3 o 4 frases;
- comentario_general: 3 o 4 frases;
- recomendaciones: entre 3 y 5;
- cada recomendación: máximo 35 palabras;
- preguntas: comenta todas las preguntas representativas recibidas;
- cada comentario de pregunta: máximo 35 palabras.

Datos:

{json.dumps(
    datos_entrada,
    ensure_ascii=False,
    separators=(",", ":"),
)}

Devuelve exactamente esta estructura:

{{
  "resumen":"",
  "comentario_general":"",
  "recomendaciones":[
    "...",
    "..."
  ],
  "preguntas":[
    {{
      "numero":1,
      "comentario":""
    }}
  ]
}}
"""

    return seleccionar_fragmento_json(
        prompt=prompt,
        modelo=modelo,
        operacion="informe",
    )