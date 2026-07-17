"""
Archivo: validar_pie.py
Ruta: core/validar_pie.py

Valida una pregunta utilizando la norma y el artículo
obtenidos del pie.

No accede a la base de datos.
"""

from core.normas import detectar_normas
from core.temario import normalizar_articulo


def crear_resultado(
    estado="A_REVISAR",
    motivo="",
    codigo_norma=None,
    articulo=None,
    parte=None,
    tema=None,
):

    return {
        "estado_validacion": estado,
        "motivo": motivo,
        "codigo_norma": codigo_norma,
        "articulo": articulo,
        "parte": parte,
        "tema": tema,
    }


def validar_pie(
    norma,
    articulo,
    temario,
    normas,
):

    if not norma:

        return crear_resultado(
            motivo=(
                "No se ha podido identificar "
                "la norma del pie."
            ),
            articulo=articulo,
        )

    detectadas = detectar_normas(
        norma,
        normas,
    )

    if len(detectadas) == 0:

        return crear_resultado(
            estado="RECHAZADA",
            motivo=(
                "La norma no pertenece al temario."
            ),
            articulo=articulo,
        )

    if len(detectadas) > 1:

        return crear_resultado(
            motivo=(
                "La referencia normativa coincide "
                "con varias normas."
            ),
            articulo=articulo,
        )

    codigo_norma = detectadas[0][
        "codigo"
    ]

    if not temario.norma_pertenece(
        codigo_norma
    ):

        return crear_resultado(
            estado="RECHAZADA",
            motivo=(
                "La norma no pertenece al temario."
            ),
            codigo_norma=codigo_norma,
            articulo=articulo,
        )

    if not articulo:

        return crear_resultado(
            motivo=(
                "La norma pertenece al temario, "
                "pero no se ha identificado el artículo."
            ),
            codigo_norma=codigo_norma,
        )

    try:

        articulo_normalizado = normalizar_articulo(
            articulo
        )

    except ValueError:

        return crear_resultado(
            motivo=(
                "El artículo extraído no tiene "
                "un formato reconocible."
            ),
            codigo_norma=codigo_norma,
            articulo=articulo,
        )

# obtener_temas_articulo() contempla:
# - documentos con cobertura por artículos;
# - documentos completos, sin límite de artículos.

    temas = temario.obtener_temas_articulo(
        codigo_norma,
        articulo_normalizado,
    )

    if len(temas) == 0:

        return crear_resultado(
            estado="RECHAZADA",
            motivo=(
                "La norma pertenece al temario, "
                "pero el artículo no está incluido."
            ),
            codigo_norma=codigo_norma,
            articulo=articulo_normalizado,
        )

    if len(temas) > 1:

        return crear_resultado(
            motivo=(
                "La norma y el artículo pertenecen "
                "al temario, pero están asociados "
                "a varios temas."
            ),
            codigo_norma=codigo_norma,
            articulo=articulo_normalizado,
        )

    tema = temas[0]

    return crear_resultado(
        estado="VALIDADA",
        motivo=(
            "La norma y el artículo del pie "
            "pertenecen al temario."
        ),
        codigo_norma=codigo_norma,
        articulo=articulo_normalizado,
        parte=tema["parte"],
        tema=tema["tema"],
    )