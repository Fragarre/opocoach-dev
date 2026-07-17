"""
Archivo: construir_prompt_explicacion.py
Ruta: core/construir_prompt_explicacion.py

Construye el prompt para generar una explicación de una pregunta.
"""


def construir_prompt(
    pregunta,
    fragmento,
):

    texto_fragmento = (
        fragmento["texto"]
        if fragmento
        else "No se dispone del fragmento legal."
    )

    referencia = ""

    if fragmento:

        if fragmento["articulo"]:

            referencia += (
                f"Artículo {fragmento['articulo']}"
            )

        if fragmento["referencia"]:

            referencia += (
                f" ({fragmento['referencia']})"
            )

    return f"""
Eres preparador de oposiciones de la Generalitat Valenciana.

Utiliza EXCLUSIVAMENTE el fragmento legal suministrado.

No inventes normativa.

No cites leyes distintas.

Devuelve únicamente un JSON válido con esta estructura:

{{
    "breve":"...",
    "extensa":"..."
}}

PREGUNTA

{pregunta["enunciado"]}

OPCIONES

A) {pregunta["opciones"]["A"]}

B) {pregunta["opciones"]["B"]}

C) {pregunta["opciones"]["C"]}

D) {pregunta["opciones"]["D"]}

RESPUESTA CORRECTA

{pregunta["respuesta_correcta"]}

REFERENCIA

{referencia}

FRAGMENTO LEGAL

{texto_fragmento}

INSTRUCCIONES

- Explica por qué la respuesta correcta es correcta.
- Explica brevemente por qué las demás opciones no son correctas, si el fragmento lo permite.
- La explicación breve tendrá una o dos frases.
- La explicación extensa tendrá entre 80 y 150 palabras.
- No añadas información que no aparezca en el fragmento.
"""