"""
Archivo: test_clasificador_real.py
Ruta: tests/test_clasificador_real.py

Dependencias:
- os
- sqlite3
- pathlib
- dotenv
- core.temario
- core.clasificador

Funcionalidad:
Valida el clasificador integrado mediante llamadas reales a la API de OpenAI.

Ejecuta tres casos controlados:

- norma conocida sin artículo;
- pregunta sin norma explícita;
- pregunta sin respaldo documental válido.

La prueba permite comprobar:

- recuperación de fragmentos mediante BM25;
- construcción y envío del prompt;
- recepción de JSON válido;
- selección de un fragmento candidato;
- aplicación de los umbrales de confianza;
- asignación de norma, artículo, parte y tema mediante Temario.

Las consultas realizadas quedan registradas en:

logs/costes_ia.csv

No modifica la base de datos.
"""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)

MODELO = "gpt-5.4-mini"


CASOS = [
    {
        "descripcion": (
            "CASO 1 — Norma conocida sin artículo"
        ),
        "pregunta": (
            "Según la Ley 39/2015, ¿cuál de los "
            "siguientes actos pone fin a la vía "
            "administrativa?"
        ),
        "opciones": {
            "A": (
                "Las resoluciones de los recursos "
                "de alzada."
            ),
            "B": (
                "Todos los actos de trámite."
            ),
            "C": (
                "Todas las solicitudes presentadas "
                "por los interesados."
            ),
            "D": (
                "Todos los informes emitidos durante "
                "el procedimiento."
            ),
        },
        "respuesta_correcta": "A",
        "estado_esperado": "VALIDADA",
        "norma_esperada": "L39_2015",
    },
    {
        "descripcion": (
            "CASO 2 — Sin norma explícita"
        ),
        "pregunta": (
            "¿Qué recurso podrá interponerse contra "
            "las resoluciones y actos que no pongan "
            "fin a la vía administrativa?"
        ),
        "opciones": {
            "A": (
                "El recurso de alzada."
            ),
            "B": (
                "El recurso de casación."
            ),
            "C": (
                "El recurso de amparo."
            ),
            "D": (
                "El recurso de revisión contable."
            ),
        },
        "respuesta_correcta": "A",
        "estado_esperado": "VALIDADA",
        "norma_esperada": "L39_2015",
    },
    {
        "descripcion": (
            "CASO 3 — Sin respaldo documental"
        ),
        "pregunta": (
            "En relación con los recursos "
            "administrativos y su regulación, "
            "¿cuál es la capital de Australia?"
        ),
        "opciones": {
            "A": "Sídney.",
            "B": "Melbourne.",
            "C": "Canberra.",
            "D": "Brisbane.",
        },
        "respuesta_correcta": "C",
        "estado_esperado": "RECHAZADA",
        "norma_esperada": None,
    },
]


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            "No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    return sqlite3.connect(
        RUTA_BD
    )


def comprobar_configuracion():

    load_dotenv()

    api_key = os.getenv(
        "OPENAI_API_KEY_OPOCOACH"
    )

    if not api_key:

        raise RuntimeError(
            "No se ha encontrado la variable "
            "OPENAI_API_KEY_OPOCOACH."
        )


def mostrar_resultado(
    resultado,
):

    print(
        f"Estado.............: "
        f"{resultado['estado']}"
    )
    print(
        f"Norma..............: "
        f"{resultado['norma']}"
    )
    print(
        f"Artículo...........: "
        f"{resultado['articulo']}"
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
        f"Fragmento..........: "
        f"{resultado['fragmento_id']}"
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


def validar_resultado(
    caso,
    resultado,
):

    errores = []

    if resultado[
        "estado"
    ] != caso[
        "estado_esperado"
    ]:

        errores.append(
            "Estado esperado "
            f"{caso['estado_esperado']} "
            "pero obtenido "
            f"{resultado['estado']}."
        )

    norma_esperada = caso[
        "norma_esperada"
    ]

    if (
        norma_esperada is not None
        and resultado["estado"] == "VALIDADA"
        and resultado["norma"] != norma_esperada
    ):

        errores.append(
            "Norma esperada "
            f"{norma_esperada} "
            "pero obtenida "
            f"{resultado['norma']}."
        )

    if resultado[
        "metodo_validacion"
    ] not in {
        "BM25",
        "BM25_IA",
    }:

        errores.append(
            "Método de validación inesperado: "
            f"{resultado['metodo_validacion']}."
        )

    if resultado[
        "estado"
    ] == "VALIDADA":

        if resultado[
            "fragmento_id"
        ] is None:

            errores.append(
                "Una pregunta VALIDADA mediante IA "
                "debe tener fragmento."
            )

        if resultado[
            "documento"
        ] is None:

            errores.append(
                "Una pregunta VALIDADA mediante IA "
                "debe tener documento."
            )

        if resultado[
            "parte"
        ] is None:

            errores.append(
                "Una pregunta VALIDADA mediante IA "
                "debe tener parte."
            )

        if resultado[
            "tema"
        ] is None:

            errores.append(
                "Una pregunta VALIDADA mediante IA "
                "debe tener tema."
            )

    return errores


def ejecutar_caso(
    clasificador,
    conn,
    caso,
):

    print()
    print(
        caso["descripcion"]
    )
    print("-" * 80)
    print(
        caso["pregunta"]
    )
    print()

    resultado = clasificador.clasificar(
        conn=conn,
        pregunta=caso["pregunta"],
        opciones=caso["opciones"],
        respuesta_correcta=(
            caso["respuesta_correcta"]
        ),
        limite_fragmentos=5,
        modelo=MODELO,
    )

    mostrar_resultado(
        resultado
    )

    errores = validar_resultado(
        caso=caso,
        resultado=resultado,
    )

    if errores:

        print()
        print("Resultado...........: ERROR")

        for error in errores:
            print(
                f"- {error}"
            )

        return 1

    print()
    print("Resultado...........: OK")

    return 0


def main():

    comprobar_configuracion()

    temario = Temario()

    clasificador = Clasificador(
        temario
    )

    conn = abrir_conexion()

    errores = 0

    try:

        print()
        print("=" * 80)
        print(
            "PRUEBA REAL DEL CLASIFICADOR"
        )
        print("=" * 80)
        print(
            f"Modelo..............: "
            f"{MODELO}"
        )
        print(
            f"Base de datos.......: "
            f"{RUTA_BD}"
        )

        for caso in CASOS:

            errores += ejecutar_caso(
                clasificador=clasificador,
                conn=conn,
                caso=caso,
            )

    finally:

        conn.close()

    print()
    print("=" * 80)

    if errores:

        print(
            f"PRUEBAS CON ERROR: {errores}"
        )

    else:

        print(
            "TODAS LAS PRUEBAS SUPERADAS"
        )

    print("=" * 80)


if __name__ == "__main__":
    main()