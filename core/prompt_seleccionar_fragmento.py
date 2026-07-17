"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : prompt_seleccionar_fragmento.py
Ruta    : core/prompt_seleccionar_fragmento.py

Objetivo:
    Construir el prompt para seleccionar un fragmento normativo.

Entradas:
    - Pregunta.
    - Fragmentos candidatos.

Salidas:
    - Prompt de selección de fragmento.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - core/clasificador.py

Flujo:
    1. Incluye pregunta y candidatos.
    2. Define el JSON esperado.

Observaciones:
    - Ninguna.

==============================================================================
"""
def construir_prompt(
    pregunta,
    opciones,
    respuesta_correcta,
    fragmentos,
):

    prompt = """
Eres un experto en normativa administrativa española.

OBJETIVO

Determinar si alguno de los fragmentos proporcionados justifica claramente
la respuesta oficial de la pregunta.

REGLAS

- Analiza el enunciado, las cuatro opciones y la respuesta oficial.
- No utilices conocimientos externos.
- Utiliza exclusivamente los fragmentos suministrados.
- No selecciones un fragmento por simple similitud terminológica.
- El fragmento debe justificar documentalmente la respuesta oficial.
- Si varios fragmentos son plausibles y no existe uno claramente superior,
  devuelve A_REVISAR.
- Si ningún fragmento justifica la respuesta oficial, devuelve RECHAZADA.
- Devuelve exclusivamente JSON válido.
"""

    prompt += "\n\nPREGUNTA\n\n"
    prompt += pregunta.strip()

    prompt += "\n\nOPCIONES\n\n"

    for letra in ("A", "B", "C", "D"):
        prompt += f"{letra}) {opciones[letra].strip()}\n"

    prompt += "\n"
    prompt += f"RESPUESTA OFICIAL: {respuesta_correcta}\n"

    prompt += "\nFRAGMENTOS CANDIDATOS\n"

    for posicion, fragmento in enumerate(
        fragmentos,
        start=1,
    ):

        prompt += "\n"
        prompt += "=" * 60 + "\n"
        prompt += f"Fragmento {posicion}\n"
        prompt += (
            f"fragmento_id="
            f"{fragmento['fragmento_id']}\n"
        )
        prompt += (
            f"documento="
            f"{fragmento['nombre_archivo']}\n"
        )
        prompt += (
            f"referencia="
            f"{fragmento['referencia']}\n\n"
        )
        prompt += fragmento["texto"].strip()
        prompt += "\n"

    prompt += """

CRITERIO DE DECISIÓN

- VALIDADA:
  Un fragmento justifica claramente la respuesta oficial.

- A_REVISAR:
  Existe respaldo plausible, pero es parcial, indirecto o ambiguo.

- RECHAZADA:
  Ningún fragmento justifica la respuesta oficial.

Devuelve EXCLUSIVAMENTE este JSON:

{
  "decision": "VALIDADA|A_REVISAR|RECHAZADA",
  "fragmento_id": 12345,
  "confianza": 0.00,
  "motivo": "Explicación breve"
}

REGLAS DEL JSON

- fragmento_id debe ser uno de los identificadores suministrados.
- Para RECHAZADA, fragmento_id debe ser null.
- confianza debe estar entre 0.00 y 1.00.
- No añadas texto fuera del JSON.
"""

    return prompt