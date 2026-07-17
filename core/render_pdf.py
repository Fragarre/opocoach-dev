"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : render_pdf.py
Ruta    : core/render_pdf.py

Objetivo:
    Generar el PDF del examen a partir de un simulacro normalizado.

Entradas:
    - Objeto Simulacro.
    - Ruta de salida.

Salidas:
    - PDF del examen.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_pdf.py

Flujo:
    1. Prepara estilos.
    2. Compone preguntas y opciones.
    3. Genera el PDF.

Observaciones:
    - Ninguna.

==============================================================================
"""
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
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
ESTILO_PREGUNTA.leading = 16
ESTILO_PREGUNTA.spaceAfter = 0.12 * cm

ESTILO_OPCION = styles["BodyText"]
ESTILO_OPCION.leftIndent = 0.7 * cm
ESTILO_OPCION.leading = 14
ESTILO_OPCION.spaceAfter = 0.06 * cm


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
            f"<b>{opcion.letra})</b> "
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

def dibujar_encabezado_pie(
    canvas,
    doc,
):

    canvas.saveState()

    numero_pagina = canvas.getPageNumber()

    if numero_pagina > 1:

        canvas.setFont(
            "Helvetica",
            9,
        )

        canvas.drawString(
            2 * cm,
            A4[1] - 1.2 * cm,
            "SIMULACRO C1-01",
        )

    canvas.setFont(
        "Helvetica",
        9,
    )

    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.1 * cm,
        f"Página {numero_pagina}",
    )

    canvas.restoreState()


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
            "GENERALITAT VALENCIANA<br/><br/>"
            "CUERPO C1-01 ADMINISTRATIVOS<br/><br/>"
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
        story,
        onFirstPage=dibujar_encabezado_pie,
        onLaterPages=dibujar_encabezado_pie,
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