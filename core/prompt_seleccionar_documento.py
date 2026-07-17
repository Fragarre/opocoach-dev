"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : prompt_seleccionar_documento.py
Ruta    : core/prompt_seleccionar_documento.py

Objetivo:
    Construir el prompt para seleccionar un documento candidato.

Entradas:
    - Pregunta.
    - Lista de documentos candidatos.

Salidas:
    - Prompt de selección documental.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - core/clasificador.py

Flujo:
    1. Enumera candidatos.
    2. Define el formato de respuesta.

Observaciones:
    - Ninguna.

==============================================================================
"""
def construir_prompt_seleccionar_documento(
    pregunta,
    opciones,
    respuesta_correcta,
    documentos,
):

    if not documentos:
        raise ValueError(
            "La lista de documentos no puede estar vacía."
        )

    respuesta_correcta = (
        respuesta_correcta.strip().upper()
    )

    if respuesta_correcta not in opciones:
        raise ValueError(
            "Respuesta correcta no válida."
        )

    partes = []

    partes.append(
        """
Eres un asistente especializado en validar preguntas de exámenes oficiales
de Informática.

Debes decidir si alguno de los documentos suministrados justifica
documentalmente la respuesta oficial.

IMPORTANTE

- Utiliza exclusivamente la información contenida en los documentos.
- No utilices conocimientos propios.
- Solo puedes seleccionar uno de los documentos proporcionados.
- Si ninguno justifica claramente la respuesta oficial, responde RECHAZADA.
- El valor de documento_id deberá corresponder exactamente con uno de los identificadores suministrados. No inventes identificadores.

La respuesta debe ser exclusivamente un objeto JSON con el formato indicado.
""".strip()
    )

    partes.append("")
    partes.append("=" * 70)
    partes.append("PREGUNTA")
    partes.append("=" * 70)
    partes.append("")
    partes.append(pregunta.strip())
    partes.append("")

    partes.append("OPCIONES")
    partes.append("")

    for letra in ("A", "B", "C", "D"):

        partes.append(
            f"{letra}) {opciones[letra]}"
        )

    partes.append("")
    partes.append(
        f"RESPUESTA OFICIAL: {respuesta_correcta}"
    )

    partes.append("")
    partes.append("=" * 70)
    partes.append("DOCUMENTOS")
    partes.append("=" * 70)

    for indice, documento in enumerate(
        documentos,
        start=1,
    ):

        partes.append("")
        partes.append("-" * 70)
        partes.append(
            f"DOCUMENTO {indice}"
        )
        partes.append("-" * 70)

        partes.append(
            f"ID: {documento['documento_id']}"
        )

        partes.append(
            f"Nombre: {documento['nombre_archivo']}"
        )

        titulo = documento.get(
            "titulo"
        )

        if titulo:

            partes.append(
                f"Título: {titulo}"
            )

        partes.append("")
        partes.append("Contenido:")
        partes.append("")
        partes.append(
            documento["texto"][:3000].strip()
        )

    partes.append("")
    partes.append("=" * 70)
    partes.append("FORMATO DE RESPUESTA")
    partes.append("=" * 70)

    partes.append(
        """
{
    "decision":"VALIDADA",
    "documento_id":62,
    "confianza":0.98,
    "motivo":"..."
}
""".strip()
    )

    partes.append("")
    partes.append(
        "Si la decisión es RECHAZADA, "
        "documento_id será null."
    )

    return "\n".join(partes)