"""
Archivo: test_clasificador_informatica_integrado.py
Ruta: tests/test_clasificador_informatica_integrado.py

Dependencias:
- sqlite3
- pathlib
- unittest.mock
- core.temario
- core.clasificador
- core.buscar_documentos_informatica

Funcionalidad:
Valida la rama integrada de clasificación de Informática mediante respuestas
simuladas de la IA.

Comprueba:

- selección de documento válido;
- asignación de parte y tema;
- confianza alta, intermedia y baja;
- respuesta RECHAZADA;
- documento inexistente;
- respuesta JSON inválida.

No llama a OpenAI.

No modifica la base de datos.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

from core.buscar_documentos_informatica import (
    buscar_documentos_informatica,
)
from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


PREGUNTA = (
    "En Microsoft Excel, ¿qué función permite "
    "sumar los valores de un rango de celdas?"
)


OPCIONES = {
    "A": "La función SUMA.",
    "B": "La función CONTAR.",
    "C": "La función PROMEDIO.",
    "D": "La función SI.",
}


def abrir_conexion():

    if not RUTA_BD.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    return sqlite3.connect(
        RUTA_BD
    )


def obtener_documento_excel(
    conn,
    temario,
):

    documentos = buscar_documentos_informatica(
        conn=conn,
        temario=temario,
        texto_consulta=(
            PREGUNTA
            + "\n"
            + OPCIONES["A"]
        ),
        limite=5,
    )

    if not documentos:
        raise RuntimeError(
            "No se han localizado documentos "
            "de Informática."
        )

    for documento in documentos:

        if documento[
            "nombre_archivo"
        ] == (
            "I_Hojas_calculo_excel_"
            "microsoft365.pdf"
        ):
            return documento

    raise RuntimeError(
        "No se ha localizado el documento "
        "de Excel."
    )


def ejecutar_caso(
    *,
    clasificador,
    conn,
    descripcion,
    respuesta_ia,
    estado_esperado,
    parte_esperada=None,
    tema_esperado=None,
):

    print()
    print(descripcion)
    print("-" * 80)

    with patch(
        "core.clasificador.seleccionar_fragmento_json",
        return_value=respuesta_ia,
    ):

        resultado = clasificador.clasificar(
            conn=conn,
            pregunta=PREGUNTA,
            opciones=OPCIONES,
            respuesta_correcta="A",
            parte_origen="Especial-Informática",
        )

    errores = 0

    if resultado[
        "estado"
    ] != estado_esperado:

        errores += 1

    if (
        parte_esperada is not None
        and resultado["parte"] != parte_esperada
    ):
        errores += 1

    if (
        tema_esperado is not None
        and resultado["tema"] != tema_esperado
    ):
        errores += 1

    print(
        f"Esperado...........: "
        f"{estado_esperado}"
    )
    print(
        f"Obtenido...........: "
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

    if errores:
        print("Resultado...........: ERROR")
        return 1

    print("Resultado...........: OK")
    return 0


def main():

    temario = Temario()
    clasificador = Clasificador(
        temario
    )

    conn = abrir_conexion()

    errores = 0

    try:

        documento_excel = obtener_documento_excel(
            conn=conn,
            temario=temario,
        )

        documento_id = documento_excel[
            "documento_id"
        ]

        print()
        print("=" * 80)
        print(
            "PRUEBA CLASIFICADOR INFORMÁTICA"
        )
        print("=" * 80)

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 1 — VALIDADA"
            ),
            respuesta_ia={
                "decision": "VALIDADA",
                "documento_id": documento_id,
                "confianza": 0.99,
                "motivo": (
                    "El documento de Excel justifica "
                    "la respuesta oficial."
                ),
            },
            estado_esperado="VALIDADA",
            parte_esperada="Especial-Informática",
            tema_esperado=20,
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 2 — Confianza intermedia"
            ),
            respuesta_ia={
                "decision": "VALIDADA",
                "documento_id": documento_id,
                "confianza": 0.80,
                "motivo": (
                    "El respaldo es plausible."
                ),
            },
            estado_esperado="A_REVISAR",
            parte_esperada="Especial-Informática",
            tema_esperado=20,
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 3 — Confianza baja"
            ),
            respuesta_ia={
                "decision": "VALIDADA",
                "documento_id": documento_id,
                "confianza": 0.30,
                "motivo": (
                    "La confianza es insuficiente."
                ),
            },
            estado_esperado="RECHAZADA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 4 — IA RECHAZADA"
            ),
            respuesta_ia={
                "decision": "RECHAZADA",
                "documento_id": None,
                "confianza": 0.20,
                "motivo": (
                    "Ningún documento justifica "
                    "la respuesta."
                ),
            },
            estado_esperado="RECHAZADA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 5 — Documento inexistente"
            ),
            respuesta_ia={
                "decision": "VALIDADA",
                "documento_id": 999999,
                "confianza": 0.99,
                "motivo": (
                    "Documento no suministrado."
                ),
            },
            estado_esperado="A_REVISAR",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 6 — JSON inválido"
            ),
            respuesta_ia={
                "decision": "ACEPTADA",
                "documento_id": documento_id,
                "confianza": 0.99,
                "motivo": (
                    "Decisión no permitida."
                ),
            },
            estado_esperado="A_REVISAR",
        )

    finally:

        conn.close()

    print()
    print("=" * 80)

    if errores:
        print(
            f"ERRORES: {errores}"
        )
    else:
        print(
            "TODAS LAS PRUEBAS SUPERADAS"
        )

    print("=" * 80)


if __name__ == "__main__":
    main()