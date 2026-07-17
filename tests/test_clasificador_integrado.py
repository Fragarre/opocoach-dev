"""
Archivo: test_clasificador_integrado.py
Ruta: tests/test_clasificador_integrado.py

Dependencias:
- pathlib
- sqlite3
- unittest.mock
- core.temario
- core.clasificador

Funcionalidad:
Valida el funcionamiento integrado del Proceso 3 de clasificación.

Comprueba mediante casos controlados:

- resolución determinista sin ejecutar BM25 ni IA;
- búsqueda BM25 limitada a una norma;
- búsqueda BM25 global dentro del temario;
- respuesta IA VALIDADA con confianza alta;
- conversión a A_REVISAR por confianza intermedia;
- conversión a RECHAZADA por confianza baja;
- respuesta IA RECHAZADA;
- rechazo de identificadores de fragmento no suministrados;
- tratamiento seguro de respuestas IA inválidas.

Las respuestas de OpenAI se simulan para que las pruebas:

- no consuman API;
- no generen costes;
- sean completamente reproducibles.

No modifica la base de datos.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path("db/oposiciones.sqlite3")


def abrir_conexion():

    if not RUTA_BD.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    return sqlite3.connect(
        RUTA_BD
    )


def obtener_fragmento_bm25(
    clasificador,
    conn,
    pregunta,
    opciones,
    respuesta_correcta,
):

    resultado_directo = (
        clasificador.clasificar_directa(
            pregunta
        )
    )

    codigo_norma = resultado_directo[
        "norma"
    ]

    texto_consulta = (
        pregunta
        + "\n"
        + opciones[
            respuesta_correcta
        ]
    )

    from core.buscar_fragmentos import (
        buscar_fragmentos,
    )

    fragmentos = buscar_fragmentos(
        conn=conn,
        temario=clasificador.temario,
        texto_consulta=texto_consulta,
        codigo_norma=codigo_norma,
        limite=5,
    )

    if not fragmentos:
        raise RuntimeError(
            "BM25 no ha localizado ningún "
            "fragmento para el caso de prueba."
        )

    return fragmentos[0]


def ejecutar_caso(
    *,
    clasificador,
    conn,
    descripcion,
    pregunta,
    opciones,
    respuesta_correcta,
    respuesta_ia,
    estado_esperado,
    metodo_esperado=None,
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
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta=respuesta_correcta,
        )

    obtenido = resultado["estado"]

    correcto = (
        obtenido == estado_esperado
    )

    if (
        correcto
        and metodo_esperado is not None
    ):
        correcto = (
            resultado["metodo_validacion"]
            == metodo_esperado
        )

    print(
        f"Esperado...........: "
        f"{estado_esperado}"
    )
    print(
        f"Obtenido...........: "
        f"{obtenido}"
    )
    print(
        f"Método.............: "
        f"{resultado['metodo_validacion']}"
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
        f"Fragmento..........: "
        f"{resultado['fragmento_id']}"
    )
    print(
        f"Confianza..........: "
        f"{resultado['confianza']}"
    )
    print(
        f"Motivo.............: "
        f"{resultado['motivo']}"
    )

    if correcto:
        print("Resultado...........: OK")
        return 0

    print("Resultado...........: ERROR")
    return 1

def probar_rechazo_varias_normas(
    clasificador,
    conn,
):

    pregunta = (
        "Señale el enunciado correcto. "
        "Según la Constitución Española y la "
        "Ley 39/2015, de 1 de octubre, del "
        "procedimiento administrativo común "
        "de las administraciones públicas:"
    )

    opciones = {
        "A": "Opción A.",
        "B": "Opción B.",
        "C": "Opción C.",
        "D": "Opción D.",
    }

    print()
    print(
        "CASO — Varias normas: rechazo directo"
    )
    print("-" * 80)

    with patch(
        "core.clasificador.buscar_fragmentos"
    ) as mock_bm25, patch(
        "core.clasificador.seleccionar_fragmento_json"
    ) as mock_ia:

        resultado = clasificador.clasificar(
            conn=conn,
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta="A",
        )

    errores = 0

    if resultado["estado"] != "RECHAZADA":

        print(
            "ERROR: se esperaba RECHAZADA "
            f"y se obtuvo {resultado['estado']}."
        )
        errores += 1

    if resultado[
        "metodo_validacion"
    ] != "DIRECTA":

        print(
            "ERROR: se esperaba método DIRECTA "
            "y se obtuvo "
            f"{resultado['metodo_validacion']}."
        )
        errores += 1

    if resultado[
        "confianza"
    ] != 1.0:

        print(
            "ERROR: se esperaba confianza 1.0 "
            f"y se obtuvo {resultado['confianza']}."
        )
        errores += 1

    if mock_bm25.called:

        print(
            "ERROR: BM25 no debía ejecutarse."
        )
        errores += 1

    if mock_ia.called:

        print(
            "ERROR: la IA no debía ejecutarse."
        )
        errores += 1

    print(
        f"Estado.............: "
        f"{resultado['estado']}"
    )
    print(
        f"Método.............: "
        f"{resultado['metodo_validacion']}"
    )
    print(
        f"Confianza..........: "
        f"{resultado['confianza']}"
    )
    print(
        f"BM25 ejecutado.....: "
        f"{mock_bm25.called}"
    )
    print(
        f"IA ejecutada.......: "
        f"{mock_ia.called}"
    )
    print(
        f"Motivo.............: "
        f"{resultado['motivo']}"
    )

    if errores == 0:

        print(
            "Resultado...........: OK"
        )

    else:

        print(
            "Resultado...........: ERROR"
        )

    return errores

def main():

    temario = Temario()
    clasificador = Clasificador(
        temario
    )

    conn = abrir_conexion()

    errores = 0

    errores += probar_rechazo_varias_normas(
    clasificador=clasificador,
    conn=conn,
    )

    try:

        print()
        print("=" * 80)
        print("PRUEBA CLASIFICADOR INTEGRADO")
        print("=" * 80)

        opciones_directa = {
            "A": "Opción A",
            "B": "Opción B",
            "C": "Opción C",
            "D": "Opción D",
        }

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 1 — Clasificación determinista"
            ),
            pregunta=(
                "Según el artículo 52 de la "
                "Ley 39/2015, señale la opción "
                "correcta."
            ),
            opciones=opciones_directa,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "RECHAZADA",
                "fragmento_id": None,
                "confianza": 0.0,
                "motivo": (
                    "Esta respuesta no debe utilizarse."
                ),
            },
            estado_esperado="VALIDADA",
            metodo_esperado="DIRECTA",
        )

        pregunta_norma = (
            "Según la Ley 39/2015, ¿cuál de los "
            "siguientes actos pone fin a la vía "
            "administrativa?"
        )

        opciones_norma = {
            "A": (
                "Las resoluciones de los recursos "
                "de alzada."
            ),
            "B": (
                "Todos los actos de trámite."
            ),
            "C": (
                "Las solicitudes presentadas por "
                "los interesados."
            ),
            "D": (
                "Todos los informes administrativos."
            ),
        }

        fragmento_norma = obtener_fragmento_bm25(
            clasificador=clasificador,
            conn=conn,
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 2 — Norma conocida, "
                "IA VALIDADA"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "VALIDADA",
                "fragmento_id": fragmento_norma[
                    "fragmento_id"
                ],
                "confianza": 0.98,
                "motivo": (
                    "El fragmento respalda "
                    "claramente la respuesta."
                ),
            },
            estado_esperado="VALIDADA",
            metodo_esperado="BM25_IA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 3 — Confianza intermedia"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "VALIDADA",
                "fragmento_id": fragmento_norma[
                    "fragmento_id"
                ],
                "confianza": 0.80,
                "motivo": (
                    "El respaldo es plausible, "
                    "pero la confianza no alcanza "
                    "el umbral."
                ),
            },
            estado_esperado="A_REVISAR",
            metodo_esperado="BM25_IA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 4 — Confianza baja"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "VALIDADA",
                "fragmento_id": fragmento_norma[
                    "fragmento_id"
                ],
                "confianza": 0.30,
                "motivo": (
                    "La confianza es insuficiente."
                ),
            },
            estado_esperado="RECHAZADA",
            metodo_esperado="BM25_IA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 5 — IA RECHAZADA"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "RECHAZADA",
                "fragmento_id": None,
                "confianza": 0.20,
                "motivo": (
                    "Ningún fragmento justifica "
                    "la respuesta oficial."
                ),
            },
            estado_esperado="RECHAZADA",
            metodo_esperado="BM25_IA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 6 — Fragmento IA inexistente"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "VALIDADA",
                "fragmento_id": 999999999,
                "confianza": 0.99,
                "motivo": (
                    "Identificador no suministrado."
                ),
            },
            estado_esperado="A_REVISAR",
            metodo_esperado="BM25_IA",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 7 — JSON IA inválido"
            ),
            pregunta=pregunta_norma,
            opciones=opciones_norma,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "ACEPTADA",
                "fragmento_id": fragmento_norma[
                    "fragmento_id"
                ],
                "confianza": 0.99,
                "motivo": (
                    "Decisión no permitida."
                ),
            },
            estado_esperado="A_REVISAR",
            metodo_esperado="BM25_IA",
        )

        pregunta_global = (
            "¿Qué recurso puede interponerse contra "
            "las resoluciones que no ponen fin a la "
            "vía administrativa?"
        )

        opciones_global = {
            "A": "El recurso de alzada.",
            "B": "El recurso de casación.",
            "C": "El recurso de amparo.",
            "D": "El recurso de revisión contable.",
        }

        fragmento_global = obtener_fragmento_bm25(
            clasificador=clasificador,
            conn=conn,
            pregunta=pregunta_global,
            opciones=opciones_global,
            respuesta_correcta="A",
        )

        errores += ejecutar_caso(
            clasificador=clasificador,
            conn=conn,
            descripcion=(
                "CASO 8 — BM25 global"
            ),
            pregunta=pregunta_global,
            opciones=opciones_global,
            respuesta_correcta="A",
            respuesta_ia={
                "decision": "VALIDADA",
                "fragmento_id": fragmento_global[
                    "fragmento_id"
                ],
                "confianza": 0.98,
                "motivo": (
                    "El fragmento justifica "
                    "la respuesta oficial."
                ),
            },
            estado_esperado="VALIDADA",
            metodo_esperado="BM25_IA",
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