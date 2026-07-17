"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : DES

Archivo : render_informe_pdf.py
Ruta    : core/render_informe_pdf.py

Objetivo:
    Generar el informe PDF completo de corrección de un intento interactivo.

==============================================================================
"""

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from typing import Any
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


styles = getSampleStyleSheet()

ESTILO_TITULO = ParagraphStyle(
    "InformeTitulo",
    parent=styles["Heading1"],
    alignment=TA_CENTER,
    spaceAfter=12,
)

ESTILO_SUBTITULO = ParagraphStyle(
    "InformeSubtitulo",
    parent=styles["Heading2"],
    spaceBefore=10,
    spaceAfter=8,
)

ESTILO_PREGUNTA = ParagraphStyle(
    "InformePregunta",
    parent=styles["Heading3"],
    spaceBefore=8,
    spaceAfter=5,
)

ESTILO_TEXTO = ParagraphStyle(
    "InformeTexto",
    parent=styles["BodyText"],
    leading=15,
    spaceAfter=5,
)

ESTILO_PEQUENO = ParagraphStyle(
    "InformePequeno",
    parent=styles["BodyText"],
    fontSize=9,
    leading=12,
    spaceAfter=4,
)


def limpiar_texto(texto):

    if texto is None:
        return ""

    return escape(str(texto))


def obtener_atributo(
    objeto: Any,
    nombre: str,
    valor_defecto: Any = "",
) -> Any:

    if isinstance(objeto, dict):
        return objeto.get(nombre, valor_defecto)

    return getattr(
        objeto,
        nombre,
        valor_defecto,
    )


def obtener_texto_opcion(opciones, letra):

    if not letra or letra == "En blanco":
        return ""

    if isinstance(opciones, dict):
        valor = opciones.get(letra, "")

        if isinstance(valor, str):
            return valor

        return obtener_atributo(
            valor,
            "texto",
            obtener_atributo(
                valor,
                "contenido",
                "",
            ),
        )

    if isinstance(opciones, (list, tuple)):

        for opcion in opciones:

            opcion_letra = obtener_atributo(
                opcion,
                "letra",
                obtener_atributo(
                    opcion,
                    "clave",
                    obtener_atributo(
                        opcion,
                        "codigo",
                        "",
                    ),
                ),
            )

            if str(opcion_letra).upper() == str(letra).upper():

                return obtener_atributo(
                    opcion,
                    "texto",
                    obtener_atributo(
                        opcion,
                        "contenido",
                        str(opcion) if isinstance(opcion, str) else "",
                    ),
                )

        indice = ord(str(letra).upper()) - ord("A")

        if 0 <= indice < len(opciones):

            opcion = opciones[indice]

            if isinstance(opcion, str):
                return opcion

            return obtener_atributo(
                opcion,
                "texto",
                obtener_atributo(
                    opcion,
                    "contenido",
                    "",
                ),
            )

    return ""

def obtener_comentarios_ia(ia):

    comentarios = {}

    for dato in ia.get("preguntas", []):

        numero = dato.get("numero")

        if numero is not None:
            comentarios[numero] = dato.get(
                "comentario",
                "",
            )

    return comentarios


def construir_resumen_temas(resultados_preguntas):

    resumen = {}

    for dato in resultados_preguntas:

        pregunta = dato["pregunta"]

        tipo = obtener_atributo(
            pregunta,
            "tipo_pregunta",
            "SIN TIPO",
        )

        tema = obtener_atributo(
            pregunta,
            "tema",
            "SIN TEMA",
        )

        clave = (
            str(tipo),
            str(tema),
        )

        if clave not in resumen:

            resumen[clave] = {
                "total": 0,
                "aciertos": 0,
                "errores": 0,
                "blancos": 0,
            }

        resumen[clave]["total"] += 1

        respuesta_usuario = dato.get(
            "respuesta_usuario",
            "En blanco",
        )

        if respuesta_usuario == "En blanco":

            resumen[clave]["blancos"] += 1

        elif dato.get("correcta", False):

            resumen[clave]["aciertos"] += 1

        else:

            resumen[clave]["errores"] += 1

    return resumen


def agregar_pie_pagina(canvas, doc):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.drawCentredString(
        A4[0] / 2,
        0.8 * cm,
        f"Página {doc.page}",
    )

    canvas.restoreState()


def generar_pdf_informe(
    ruta_pdf,
    convocatoria,
    identificador,
    resultado_correccion,
):

    ruta_pdf = Path(ruta_pdf)

    ruta_pdf.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    aciertos = resultado_correccion["aciertos"]
    errores = resultado_correccion["errores"]
    blancos = resultado_correccion["blancos"]
    nota = resultado_correccion["nota"]

    resultados_preguntas = resultado_correccion.get(
        "resultados_preguntas",
        [],
    )

    ia = resultado_correccion.get(
        "ia",
        {},
    )

    comentarios_ia = obtener_comentarios_ia(
        ia
    )

    doc = SimpleDocTemplate(
        str(ruta_pdf),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.5 * cm,
    )

    fecha = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    penalizacion = errores / 3

    story: list[Flowable] = [
        Paragraph(
            "INFORME DE CORRECCIÓN",
            ESTILO_TITULO,
        ),
    ]

    datos_resumen = [
        ["Convocatoria", limpiar_texto(convocatoria)],
        ["Simulacro", limpiar_texto(identificador)],
        ["Fecha", fecha],
        ["Aciertos", str(aciertos)],
        ["Errores", str(errores)],
        ["En blanco", str(blancos)],
        [
            "Penalización",
            f"{penalizacion:.2f} puntos",
        ],
        ["Nota", f"{nota:.2f} / 10"],
    ]

    tabla_resumen = Table(
        datos_resumen,
        colWidths=[
            5 * cm,
            10 * cm,
        ],
    )

    tabla_resumen.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.whitesmoke,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.extend(
        [
            tabla_resumen,
            Spacer(1, 0.5 * cm),
            Paragraph(
                (
                    "La nota se calcula sobre 10. "
                    "Cada respuesta incorrecta penaliza "
                    "un tercio de una respuesta correcta. "
                    "Las respuestas en blanco no suman "
                    "ni restan."
                ),
                ESTILO_PEQUENO,
            ),
        ]
    )

    resumen_ia = ia.get(
        "resumen",
        "",
    )

    comentario_general = ia.get(
        "comentario_general",
        "",
    )

    if resumen_ia or comentario_general:

        story.append(
            Paragraph(
                "ANÁLISIS GENERAL",
                ESTILO_SUBTITULO,
            )
        )

        if resumen_ia:

            story.append(
                Paragraph(
                    limpiar_texto(resumen_ia),
                    ESTILO_TEXTO,
                )
            )

        if comentario_general:

            story.append(
                Paragraph(
                    limpiar_texto(
                        comentario_general
                    ),
                    ESTILO_TEXTO,
                )
            )

    resumen_temas = construir_resumen_temas(
        resultados_preguntas
    )

    if resumen_temas:

        story.append(
            Paragraph(
                "RENDIMIENTO POR TEMA",
                ESTILO_SUBTITULO,
            )
        )

        datos_temas = [
            [
                "Bloque",
                "Tema",
                "Total",
                "Aciertos",
                "Errores",
                "Blancos",
            ]
        ]

        for clave in sorted(
            resumen_temas,
            key=lambda valor: (
                valor[0],
                valor[1],
            ),
        ):

            tipo, tema = clave
            dato = resumen_temas[clave]

            datos_temas.append(
                [
                    limpiar_texto(tipo),
                    limpiar_texto(tema),
                    str(dato["total"]),
                    str(dato["aciertos"]),
                    str(dato["errores"]),
                    str(dato["blancos"]),
                ]
            )

        tabla_temas = Table(
            datos_temas,
            repeatRows=1,
            colWidths=[
                5.2 * cm,
                2 * cm,
                1.8 * cm,
                2 * cm,
                1.8 * cm,
                1.8 * cm,
            ],
        )

        tabla_temas.setStyle(
            TableStyle(
                [
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.grey,
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.whitesmoke,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "ALIGN",
                        (2, 1),
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
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(
            tabla_temas
        )

    preguntas_no_acertadas = [
        dato
        for dato in resultados_preguntas
        if not dato.get("correcta", False)
    ]

    if preguntas_no_acertadas:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "PREGUNTAS NO ACERTADAS",
                ESTILO_SUBTITULO,
            )
        )

        for dato in preguntas_no_acertadas:

            pregunta = dato["pregunta"]

            numero = dato.get(
                "numero",
                obtener_atributo(
                    pregunta,
                    "numero",
                    "",
                ),
            )

            respuesta_usuario = dato.get(
                "respuesta_usuario",
                "En blanco",
            )

            respuesta_correcta = obtener_atributo(
                pregunta,
                "respuesta_correcta",
                "",
            )

            opciones = obtener_atributo(
                pregunta,
                "opciones",
                {},
            )

            texto_usuario = obtener_texto_opcion(
                opciones,
                respuesta_usuario,
            )

            texto_correcta = obtener_texto_opcion(
                opciones,
                respuesta_correcta,
            )

            if not texto_correcta:

                texto_correcta = obtener_atributo(
                    pregunta,
                    "texto_respuesta_correcta",
                    "",
                )

            norma = obtener_atributo(
                pregunta,
                "norma",
                "",
            )

            articulo = obtener_atributo(
                pregunta,
                "articulo",
                "",
            )

            tema = obtener_atributo(
                pregunta,
                "tema",
                "",
            )

            tipo = obtener_atributo(
                pregunta,
                "tipo_pregunta",
                "",
            )

            explicacion = obtener_atributo(
                pregunta,
                "explicacion",
                "",
            )

            comentario = comentarios_ia.get(
                numero,
                "",
            )

            bloque = [
                Paragraph(
                    f"Pregunta {limpiar_texto(numero)}",
                    ESTILO_PREGUNTA,
                ),
                Paragraph(
                    (
                        f"<b>Bloque:</b> "
                        f"{limpiar_texto(tipo)} · "
                        f"<b>Tema:</b> "
                        f"{limpiar_texto(tema)}"
                    ),
                    ESTILO_PEQUENO,
                ),
                Paragraph(
                    (
                        f"<b>Respuesta elegida:</b> "
                        f"{limpiar_texto(respuesta_usuario)}"
                        + (
                            f") {limpiar_texto(texto_usuario)}"
                            if texto_usuario
                            else ""
                        )
                    ),
                    ESTILO_TEXTO,
                ),
                Paragraph(
                    (
                        f"<b>Respuesta correcta:</b> "
                        f"{limpiar_texto(respuesta_correcta)}"
                        + (
                            f") {limpiar_texto(texto_correcta)}"
                            if texto_correcta
                            else ""
                        )
                    ),
                    ESTILO_TEXTO,
                ),
            ]

            if explicacion:

                bloque.append(
                    Paragraph(
                        (
                            f"<b>Explicación:</b> "
                            f"{limpiar_texto(explicacion)}"
                        ),
                        ESTILO_TEXTO,
                    )
                )

            referencia = " · ".join(
                parte
                for parte in [
                    str(norma).strip(),
                    str(articulo).strip(),
                ]
                if parte
            )

            if referencia:

                bloque.append(
                    Paragraph(
                        (
                            f"<b>Referencia normativa:</b> "
                            f"{limpiar_texto(referencia)}"
                        ),
                        ESTILO_TEXTO,
                    )
                )

            if comentario:

                bloque.append(
                    Paragraph(
                        (
                            f"<b>Comentario IA:</b> "
                            f"{limpiar_texto(comentario)}"
                        ),
                        ESTILO_TEXTO,
                    )
                )

            story.extend(bloque)

            story.append(
                Spacer(
                    1,
                    0.25 * cm,
                )
            )

    recomendaciones = ia.get(
        "recomendaciones",
        [],
    )

    if recomendaciones:

        story.append(
            Paragraph(
                "RECOMENDACIONES DE ESTUDIO",
                ESTILO_SUBTITULO,
            )
        )

        for recomendacion in recomendaciones:

            story.append(
                Paragraph(
                    (
                        "• "
                        + limpiar_texto(
                            recomendacion
                        )
                    ),
                    ESTILO_TEXTO,
                )
            )

    doc.build(story)

    return ruta_pdf