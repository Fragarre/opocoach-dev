"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : render_soluciones_pdf.py
Ruta    : core/render_soluciones_pdf.py

Objetivo:
    Generar el PDF de soluciones y explicaciones de un simulacro.

Entradas:
    - Objeto Simulacro.
    - Ruta de salida.

Salidas:
    - PDF de soluciones.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_pdf.py

Flujo:
    1. Recupera respuestas.
    2. Compone soluciones.
    3. Genera el PDF.

Observaciones:
    - Ninguna.

==============================================================================
"""
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    CondPageBreak,
)
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    CondPageBreak,
    Table,
    TableStyle,
)
from reportlab.lib import colors

import csv
from pathlib import Path



styles = getSampleStyleSheet()

ROOT = Path(__file__).resolve().parents[1]

RUTA_NORMAS = (
    ROOT
    / "config"
    / "normas.csv"
)


def cargar_normas():

    normas = {}

    with open(
        RUTA_NORMAS,
        encoding="utf-8-sig",
        newline="",
    ) as f:

        lector = csv.DictReader(
            f,
            delimiter=";",
        )

        for fila in lector:

            codigo = (
                fila["codigo"]
                .strip()
            )

            normas[codigo] = (
                fila["titulo_corto"]
                .strip()
            )

    return normas


NORMAS = cargar_normas()

ESTILO_TITULO = styles["Heading1"]
ESTILO_TITULO.alignment = TA_CENTER

ESTILO_PREGUNTA = styles["Heading2"]
ESTILO_PREGUNTA.spaceBefore = 0
ESTILO_PREGUNTA.spaceAfter = 0.25 * cm

ESTILO_TEXTO = styles["BodyText"]
ESTILO_TEXTO.leading = 15
ESTILO_TEXTO.spaceAfter = 0.15 * cm

ESTILO_OPCION = styles["BodyText"]
ESTILO_OPCION.leftIndent = 0.7 * cm
ESTILO_OPCION.leading = 14
ESTILO_OPCION.spaceAfter = 0.08 * cm

ESTILO_CORRECTA = styles["BodyText"]
ESTILO_CORRECTA.leading = 15
ESTILO_CORRECTA.spaceBefore = 0.2 * cm
ESTILO_CORRECTA.spaceAfter = 0.25 * cm

ESTILO_REFERENCIA = styles["BodyText"]
ESTILO_REFERENCIA.leading = 14
ESTILO_REFERENCIA.spaceBefore = 0.15 * cm
ESTILO_REFERENCIA.spaceAfter = 0.15 * cm

ESTILO_FRAGMENTO = styles["BodyText"]
ESTILO_FRAGMENTO.leftIndent = 0.5 * cm
ESTILO_FRAGMENTO.rightIndent = 0.5 * cm
ESTILO_FRAGMENTO.leading = 14
ESTILO_FRAGMENTO.spaceAfter = 0.3 * cm


def limpiar_texto(
    texto,
):

    if texto is None:
        return ""

    texto = str(texto)

    reemplazos = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "ft",
        "\ufb06": "st",
    }

    for origen, destino in reemplazos.items():

        texto = texto.replace(
            origen,
            destino,
        )

    return escape(
        texto
    ).replace(
        "\n",
        "<br/>",
    )


def obtener_opcion_correcta(
    pregunta,
):

    for opcion in pregunta.opciones:

        if (
            opcion.letra
            == pregunta.respuesta_correcta
        ):

            return opcion.texto

    return (
        pregunta.texto_respuesta_correcta
        or ""
    )

def crear_tabla_respuestas(
    simulacro,
):

    respuestas = [
        (
            pregunta.numero,
            pregunta.respuesta_correcta,
        )
        for pregunta in simulacro.preguntas
    ]

    columnas = 4
    filas_por_columna = 28

    datos = []

    for fila in range(
        filas_por_columna
    ):

        fila_tabla = []

        for columna in range(
            columnas
        ):

            indice = (
                columna * filas_por_columna
                + fila
            )

            if indice < len(respuestas):

                numero, respuesta = respuestas[
                    indice
                ]

                fila_tabla.append(
                    f"{numero}. {respuesta}"
                )

            else:

                fila_tabla.append(
                    ""
                )

        datos.append(
            fila_tabla
        )

    tabla = Table(
        datos,
        colWidths=[
            4 * cm,
            4 * cm,
            4 * cm,
            4 * cm,
        ],
    )

    tabla.setStyle(
        TableStyle(
            [
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.grey,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [
                        colors.white,
                        colors.whitesmoke,
                    ],
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return tabla

def bloque_solucion(
    pregunta,
):

    elementos = []

    elementos.append(
        CondPageBreak(
            7 * cm
        )
    )

    elementos.append(
        Paragraph(
            f"Pregunta {pregunta.numero}",
            ESTILO_PREGUNTA,
        )
    )

    elementos.append(
        Paragraph(
            limpiar_texto(
                pregunta.enunciado
            ),
            ESTILO_TEXTO,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.1 * cm,
        )
    )

    texto_correcta = obtener_opcion_correcta(
        pregunta
    )

    elementos.append(
        Paragraph(
            (
                "<b>Respuesta correcta: "
                f"{pregunta.respuesta_correcta})</b> "
                f"{limpiar_texto(texto_correcta)}"
            ),
            ESTILO_CORRECTA,
        )
    )

    explicacion = (
        pregunta.explicacion
        or {}
    )

    breve = explicacion.get(
        "breve",
        "",
    )

    extensa = explicacion.get(
        "extensa",
        "",
    )

    if breve:

        elementos.append(
            Paragraph(
                "<b>Explicación breve</b>",
                ESTILO_TEXTO,
            )
        )

        elementos.append(
            Paragraph(
                limpiar_texto(
                    breve
                ),
                ESTILO_TEXTO,
            )
        )


    referencia = []

    if pregunta.norma:

        nombre_norma = NORMAS.get(
            pregunta.norma,
            pregunta.norma,
        )

        referencia.append(
            limpiar_texto(
                nombre_norma
            )
        )

    if pregunta.articulo:

        referencia.append(
            "Artículo "
            + limpiar_texto(
                pregunta.articulo
            )
        )

    if referencia:

        elementos.append(
            Paragraph(
                (
                    "<b>Referencia:</b> "
                    + " — ".join(
                        referencia
                    )
                ),
                ESTILO_REFERENCIA,
            )
        )

    return elementos


def generar_pdf_soluciones(
    simulacro,
    ruta_pdf,
):

    doc = SimpleDocTemplate(
        str(ruta_pdf),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    story.append(
        Paragraph(
            "SOLUCIONES DEL SIMULACRO",
            ESTILO_TITULO,
        )
    )

    story.append(
    crear_tabla_respuestas(
        simulacro
    )
    )

    story.append(
        PageBreak()
    )

    story.append(
        Spacer(
            1,
            0.8 * cm,
        )
    )

    for pregunta in simulacro.preguntas:

        story.extend(
            bloque_solucion(
                pregunta
            )
        )

    doc.build(
        story
    )