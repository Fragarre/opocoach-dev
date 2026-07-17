"""
Archivo: test_clasificador_informatica_real.py
Ruta: tests/test_clasificador_informatica_real.py

Dependencias:
- sqlite3
- pathlib
- core.temario
- core.clasificador

Funcionalidad:
Valida la rama de Informática mediante una llamada real a OpenAI.

Comprueba:

- búsqueda BM25 documental;
- selección del documento correcto;
- asignación de parte y tema;
- aplicación de confianza;
- respuesta JSON válida.

No modifica la base de datos.
"""

import sqlite3
from pathlib import Path

from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)

MODELO = "gpt-5.4-mini"


def main():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    pregunta = (
        "En Microsoft Excel, ¿qué función permite "
        "sumar los valores de un rango de celdas?"
    )

    opciones = {
        "A": "La función SUMA.",
        "B": "La función CONTAR.",
        "C": "La función PROMEDIO.",
        "D": "La función SI.",
    }

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        temario = Temario()

        clasificador = Clasificador(
            temario
        )

        print()
        print("=" * 80)
        print(
            "PRUEBA REAL CLASIFICADOR INFORMÁTICA"
        )
        print("=" * 80)

        resultado = clasificador.clasificar(
            conn=conn,
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta="A",
            parte_origen="Especial-Informática",
            limite_fragmentos=3,
            modelo=MODELO,
        )

        print()
        print(
            f"Estado.............: "
            f"{resultado['estado']}"
        )
        print(
            f"Parte..............: "
            f"{resultado['parte']}"
        )
        print(
            f"Tema...............: "
            f"{resultado['tema']}"
        )
        print(
            f"Documento..........: "
            f"{resultado['documento']}"
        )
        print(
            f"Confianza..........: "
            f"{resultado['confianza']}"
        )
        print(
            f"Método.............: "
            f"{resultado['metodo_validacion']}"
        )
        print(
            f"Motivo.............: "
            f"{resultado['motivo']}"
        )

        errores = 0

        if resultado["estado"] != "VALIDADA":
            errores += 1

        if resultado["parte"] != "Especial-Informática":
            errores += 1

        if resultado["tema"] != 20:
            errores += 1

        if resultado["documento"] != (
            "I_Hojas_calculo_excel_microsoft365.pdf"
        ):
            errores += 1

        print()
        print("=" * 80)

        if errores:

            print(
                f"RESULTADO: ERROR ({errores})"
            )

        else:

            print(
                "RESULTADO: PRUEBA SUPERADA"
            )

        print("=" * 80)

    finally:

        conn.close()


if __name__ == "__main__":
    main()