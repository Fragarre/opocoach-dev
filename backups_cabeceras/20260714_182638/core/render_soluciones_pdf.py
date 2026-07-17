"""
Archivo: render_soluciones_pdf.py
Ruta: core/render_soluciones_pdf.py

Genera el solucionario del simulacro en PDF.
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


styles = getSampleStyleSheet()

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

    if extensa:

        elementos.append(
            Paragraph(
                "<b>Explicación</b>",
                ESTILO_TEXTO,
            )
        )

        elementos.append(
            Paragraph(
                limpiar_texto(
                    extensa
                ),
                ESTILO_TEXTO,
            )
        )

    referencia = []

    if pregunta.norma:

        referencia.append(
            limpiar_texto(
                pregunta.norma
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

    fragmento = (
        pregunta.fragmento
        or {}
    )

    texto_fragmento = fragmento.get(
        "texto"
    )

    if texto_fragmento:

        elementos.append(
            Paragraph(
                "<b>Fragmento de apoyo</b>",
                ESTILO_TEXTO,
            )
        )

        elementos.append(
            Paragraph(
                limpiar_texto(
                    texto_fragmento
                ),
                ESTILO_FRAGMENTO,
            )
        )

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
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