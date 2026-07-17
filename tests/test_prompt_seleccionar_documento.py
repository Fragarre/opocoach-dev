"""
Archivo: test_prompt_seleccionar_documento.py
Ruta: tests/test_prompt_seleccionar_documento.py

Comprueba la construcción del prompt para la selección de
documentos de Informática.

No llama a OpenAI.
"""

import sqlite3
from pathlib import Path

from core.buscar_documentos_informatica import (
    buscar_documentos_informatica,
)
from core.prompt_seleccionar_documento import (
    construir_prompt_seleccionar_documento,
)
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


def main():

    conn = sqlite3.connect(RUTA_BD)

    try:

        temario = Temario()

        pregunta = (
            "En Microsoft Excel, ¿qué función permite "
            "sumar los valores de un rango de celdas?"
        )

        opciones = {
            "A": "SUMA",
            "B": "CONTAR",
            "C": "PROMEDIO",
            "D": "SI",
        }

        documentos = buscar_documentos_informatica(
            conn=conn,
            temario=temario,
            texto_consulta=(
                pregunta
                + "\n"
                + opciones["A"]
            ),
            limite=3,
        )

        prompt = construir_prompt_seleccionar_documento(
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta="A",
            documentos=documentos,
        )

        print()
        print("=" * 80)
        print("PROMPT DOCUMENTOS")
        print("=" * 80)
        print(prompt)

        print()
        print("=" * 80)
        print(
            f"Longitud: {len(prompt):,} caracteres"
        )
        print("=" * 80)

    finally:

        conn.close()


if __name__ == "__main__":
    main()