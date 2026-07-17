"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : EN DESARROLLO

Archivo : clasificar_data_informatica.py
Ruta    : procesos/clasificar_data_informatica.py

Objetivo:
    Resolver por lotes la respuesta correcta, el tema y una explicación breve
    de las preguntas extraídas desde data_informatica.

Entradas:
    - JSON *_extraido.json de importaciones/informatica.

Salidas:
    - JSON *_clasificado.json.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.openai_api
    - json
    - pathlib

Flujo:
    1. Cargar preguntas extraídas.
    2. Dividirlas en lotes.
    3. Enviar cada lote a OpenAI.
    4. Validar las respuestas.
    5. Guardar el JSON clasificado.

Observaciones:
    - No escribe en la base de datos.
    - Todas las llamadas a OpenAI pasan por core.openai_api.

==============================================================================
"""

import argparse
import json
from pathlib import Path

from core.openai_api import seleccionar_fragmento_json


ROOT = Path(__file__).resolve().parents[1]

RUTA_IMPORTACIONES = (
    ROOT
    / "importaciones"
    / "informatica"
)

MODELO_IA = "gpt-5.4-mini"

TAMANO_LOTE = 20

MATERIAS_INFORMATICA = {
    "INFORMATICA_BASICA": (
        "Informática básica, hardware, software, redes, "
        "seguridad y conceptos generales"
    ),
    "WINDOWS_11": (
        "Sistema operativo Windows 11"
    ),
    "EXPLORADOR_WINDOWS_11": (
        "Explorador de archivos de Windows 11"
    ),
    "OUTLOOK_365": (
        "Correo electrónico Outlook de Microsoft 365"
    ),
    "WORD_365": (
        "Procesador de textos Word de Microsoft 365"
    ),
    "EXCEL_365": (
        "Hojas de cálculo Excel de Microsoft 365"
    ),
    "TEAMS_365": (
        "Plataforma colaborativa Teams de Microsoft 365"
    ),
    "NAVEGADORES_WEB": (
        "Navegadores web"
    ),
    "INTELIGENCIA_ARTIFICIAL": (
        "Herramientas de Inteligencia Artificial"
    ),
}

def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Clasifica preguntas de informática "
            "extraídas previamente a JSON."
        )
    )

    parser.add_argument(
        "json",
        help=(
            "Nombre o ruta del JSON *_extraido.json."
        ),
    )

    return parser.parse_args()


def resolver_json(
    valor,
):

    ruta = Path(
        valor
    )

    if ruta.exists():

        return ruta.resolve()

    ruta = (
        RUTA_IMPORTACIONES
        / ruta.name
    )

    if ruta.exists():

        return ruta.resolve()

    raise FileNotFoundError(
        f"No existe el JSON: {valor}"
    )


def cargar_json(
    ruta_json,
):

    return json.loads(
        ruta_json.read_text(
            encoding="utf-8",
        )
    )


def dividir_lotes(
    preguntas,
):

    for inicio in range(
        0,
        len(preguntas),
        TAMANO_LOTE,
    ):

        yield preguntas[
            inicio:inicio + TAMANO_LOTE
        ]

def construir_prompt_lote(
    lote,
):

    materias = "\n".join(
        f"{codigo}: {descripcion}"
        for codigo, descripcion
        in MATERIAS_INFORMATICA.items()
    )

    preguntas = []

    for pregunta in lote:

        opciones = pregunta["opciones"]

        preguntas.append(
            {
                "numero": pregunta["numero_original"],
                "enunciado": pregunta["enunciado"],
                "opciones": {
                    "A": opciones["A"],
                    "B": opciones["B"],
                    "C": opciones["C"],
                    "D": opciones["D"],
                },
            }
        )

    return f"""
Analiza las siguientes preguntas de informática para una oposición.

Para cada pregunta debes:

1. Determinar la respuesta correcta.
2. Clasificarla en UNA de las materias permanentes indicadas abajo.
3. Dar una explicación breve y precisa.
4. Indicar una confianza entre 0 y 1.

La clasificación NO depende de ninguna convocatoria ni de ningún tema del temario. Debes devolver exclusivamente el código de la materia.

Materias:

{materias}

Preguntas:

{json.dumps(
    preguntas,
    ensure_ascii=False,
    indent=2,
)}

Devuelve exclusivamente JSON válido con esta estructura:

{{
  "resultados": [
    {{
      "numero": 1,
      "respuesta_correcta": "A",
      "materia": "WORD_365",
      "explicacion_breve": "Texto breve.",
      "confianza": 0.98
    }}
  ]
}}
""".strip()

def validar_resultados_lote(
    lote,
    respuesta,
):

    resultados = respuesta.get(
        "resultados",
        []
    )

    por_numero = {
        item.get("numero"): item
        for item in resultados
        if isinstance(item, dict)
    }

    salida = []

    for pregunta in lote:

        numero = pregunta[
            "numero_original"
        ]

        item = por_numero.get(
            numero
        )

        if item is None:

            salida.append(
                {
                    "numero": numero,
                    "respuesta_correcta": None,
                    "materia": None,
                    "explicacion_breve": "",
                    "confianza": 0.0,
                    "incidencia": (
                        "La IA no devolvió resultado."
                    ),
                }
            )

            continue

        respuesta_correcta = str(
            item.get(
                "respuesta_correcta",
                "",
            )
        ).strip().upper()

        materia = str(
            item.get(
                "materia",
                "",
            )
        ).strip().upper()

        explicacion = str(
            item.get(
                "explicacion_breve",
                "",
            )
        ).strip()

        try:

            confianza = float(
                item.get(
                    "confianza",
                    0.0,
                )
            )

        except (TypeError, ValueError):

            confianza = 0.0

        incidencia = None

        if respuesta_correcta not in {
            "A",
            "B",
            "C",
            "D",
        }:

            respuesta_correcta = None

            incidencia = (
                "Respuesta correcta no válida."
            )

        if materia not in MATERIAS_INFORMATICA:

            materia = None

            incidencia = (
                "Materia no válida."
                if incidencia is None
                else incidencia
                + " Materia no válida."
            )

        salida.append(
            {
                "numero": numero,
                "respuesta_correcta": (
                    respuesta_correcta
                ),
                "materia": materia,
                "explicacion_breve": explicacion,
                "confianza": confianza,
                "incidencia": incidencia,
            }
        )

    return salida


def clasificar_lote(
    lote,
):

    prompt = construir_prompt_lote(
        lote
    )

    respuesta = seleccionar_fragmento_json(
        prompt=prompt,
        modelo=MODELO_IA,
        operacion=(
            "informatica_clasificacion_lote"
        ),
    )

    return validar_resultados_lote(
        lote=lote,
        respuesta=respuesta,
    )

def guardar_clasificado(
    ruta_json,
    datos_originales,
    resultados,
):

    resultados_por_numero = {
        resultado["numero"]: resultado
        for resultado in resultados
    }

    preguntas_clasificadas = []

    for pregunta in datos_originales["preguntas"]:

        numero = pregunta["numero_original"]

        clasificacion = resultados_por_numero.get(
            numero,
            {
                "numero": numero,
                "respuesta_correcta": None,
                "materia": None,
                "explicacion_breve": "",
                "confianza": 0.0,
                "incidencia": (
                    "No existe clasificación."
                ),
            },
        )

        preguntas_clasificadas.append(
            {
                **pregunta,
                "clasificacion": clasificacion,
            }
        )

    ruta_salida = ruta_json.with_name(
        ruta_json.name.replace(
            "_extraido.json",
            "_clasificado.json",
        )
    )

    contenido = {
        "pdf": datos_originales.get("pdf"),
        "ruta_pdf": datos_originales.get(
            "ruta_pdf"
        ),
        "preguntas_detectadas": len(
            preguntas_clasificadas
        ),
        "modelo_ia": MODELO_IA,
        "preguntas": preguntas_clasificadas,
    }

    ruta_salida.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return ruta_salida

def main():

    argumentos = crear_argumentos()

    ruta_json = resolver_json(
        argumentos.json
    )

    datos = cargar_json(
        ruta_json
    )

    preguntas = datos.get(
        "preguntas",
        []
    )

    if not preguntas:

        raise ValueError(
            "El JSON no contiene preguntas."
        )

    resultados = []

    lotes = list(
        dividir_lotes(
            preguntas
        )
    )

    print()
    print("=" * 70)
    print("CLASIFICACIÓN DE INFORMÁTICA")
    print("=" * 70)
    print(
        f"Preguntas..........: {len(preguntas)}"
    )
    print(
        f"Lotes..............: {len(lotes)}"
    )

    for indice, lote in enumerate(
        lotes,
        start=1,
    ):

        print()
        print(
            f"Lote {indice}/{len(lotes)} "
            f"({len(lote)} preguntas)"
        )

        resultados.extend(
            clasificar_lote(
                lote
            )
        )

    ruta_salida = guardar_clasificado(
        ruta_json=ruta_json,
        datos_originales=datos,
        resultados=resultados,
    )

    incidencias = sum(
        1
        for resultado in resultados
        if resultado["incidencia"] is not None
    )

    print()
    print("=" * 70)
    print("CLASIFICACIÓN FINALIZADA")
    print("=" * 70)
    print(
        f"Resultados.........: {len(resultados)}"
    )
    print(
        f"Incidencias........: {incidencias}"
    )
    print(
        f"JSON...............: {ruta_salida}"
    )
    print("=" * 70)


if __name__ == "__main__":

    main()

