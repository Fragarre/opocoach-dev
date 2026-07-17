"""
Archivo: render_pdf.py
Ruta: render/render_pdf.py

Genera el examen en PDF.
"""

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    KeepTogether,
)


styles = getSampleStyleSheet()


ESTILO_TITULO = styles["Heading1"]
ESTILO_TITULO.alignment = TA_CENTER

ESTILO_PREGUNTA = styles["BodyText"]
ESTILO_PREGUNTA.leading = 18
ESTILO_PREGUNTA.spaceAfter = 0

ESTILO_OPCION = styles["BodyText"]
ESTILO_OPCION.leftIndent = 0.7 * cm
ESTILO_OPCION.leading = 16


def bloque_pregunta(
    pregunta,
):

    elementos = []

    elementos.append(
        Paragraph(
            f"<b>{pregunta.numero}.</b> "
            f"{limpiar_texto(pregunta.enunciado)}",
            ESTILO_PREGUNTA,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.15 * cm,
        )
    )

    for opcion in pregunta.opciones:

        elementos.append(
            Paragraph(
                f"□ <b>{opcion.letra})</b> "
                f"{limpiar_texto(opcion.texto)}",
                ESTILO_OPCION,
            )
        )

    elementos.append(
        Spacer(
            1,
            0.35 * cm,
        )
    )

    return KeepTogether(
        elementos
    )


def generar_pdf(
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
            "SIMULACRO DE EXAMEN",
            ESTILO_TITULO,
        )
    )

    story.append(
        Spacer(
            1,
            0.8 * cm,
        )
    )

    for pregunta in simulacro.preguntas:

        story.append(
            bloque_pregunta(
                pregunta
            )
        )

    doc.build(
        story
    )

def limpiar_texto(texto):

    if texto is None:
        return ""

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

    return texto