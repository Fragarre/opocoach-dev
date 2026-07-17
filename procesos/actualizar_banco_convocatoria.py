"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : EN DESARROLLO

Archivo : actualizar_banco_convocatoria.py
Ruta    : procesos/actualizar_banco_convocatoria.py

Objetivo:
    Regenerar el banco de preguntas de una convocatoria a partir de las
    evaluaciones ACEPTADA existentes para dicha convocatoria.

Entradas:
    - Código CFG de convocatoria.

Salidas:
    - banco_preguntas
    - banco_opciones

Modifica BD:
    Sí

Tablas afectadas:
    - banco_preguntas
    - banco_opciones

Flujo:
    1. Localizar la convocatoria.
    2. Eliminar el banco actual de esa convocatoria.
    3. Recuperar evaluaciones ACEPTADA.
    4. Insertar preguntas y opciones.
    5. Mostrar resumen.

==============================================================================
"""

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Regenera el banco de una convocatoria "
            "desde sus evaluaciones."
        )
    )

    parser.add_argument(
        "codigo_cfg",
        help="Código CFG de la convocatoria.",
    )

    return parser.parse_args()


def abrir_conexion():

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn

def obtener_convocatoria(
    conn,
    codigo_cfg,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (
            codigo_cfg,
        ),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            f"No existe la convocatoria {codigo_cfg!r}."
        )

    return fila["id"]


def vaciar_banco_convocatoria(
    conn,
    convocatoria_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM banco_preguntas
        WHERE convocatoria_id = ?
        """,
        (
            convocatoria_id,
        ),
    )

    return cur.rowcount

def obtener_evaluaciones_aceptadas(
    conn,
    convocatoria_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            epc.pregunta_importada_id,
            epc.parte_id,
            epc.tema_id,
            epc.fragmento_id,

            pi.enunciado,
            pi.respuesta_correcta

        FROM evaluaciones_preguntas_convocatoria epc

        JOIN preguntas_importadas pi
            ON pi.id = epc.pregunta_importada_id

        WHERE
            epc.convocatoria_id = ?
            AND epc.decision = 'ACEPTADA'
            AND epc.parte_id IS NOT NULL
            AND epc.tema_id IS NOT NULL
            AND pi.respuesta_correcta IN (
                'A',
                'B',
                'C',
                'D'
            )

        ORDER BY epc.pregunta_importada_id
        """,
        (
            convocatoria_id,
        ),
    )

    return cur.fetchall()

def obtener_opciones_importadas(
    conn,
    pregunta_importada_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            letra,
            texto
        FROM opciones_importadas
        WHERE pregunta_importada_id = ?
        ORDER BY letra
        """,
        (
            pregunta_importada_id,
        ),
    )

    return cur.fetchall()


def insertar_banco_pregunta(
    conn,
    convocatoria_id,
    evaluacion,
):

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO banco_preguntas (
            pregunta_importada_id,
            convocatoria_id,
            parte_id,
            tema_id,
            fragmento_id,
            enunciado,
            respuesta_correcta,
            estado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'VALIDADA')
        """,
        (
            evaluacion["pregunta_importada_id"],
            convocatoria_id,
            evaluacion["parte_id"],
            evaluacion["tema_id"],
            evaluacion["fragmento_id"],
            evaluacion["enunciado"],
            evaluacion["respuesta_correcta"],
        ),
    )

    return cur.lastrowid


def insertar_banco_opciones(
    conn,
    banco_pregunta_id,
    opciones,
):

    if len(opciones) != 4:

        raise ValueError(
            "La pregunta importada no tiene "
            "exactamente cuatro opciones."
        )

    cur = conn.cursor()

    for opcion in opciones:

        cur.execute(
            """
            INSERT INTO banco_opciones (
                banco_pregunta_id,
                letra,
                texto
            )
            VALUES (?, ?, ?)
            """,
            (
                banco_pregunta_id,
                opcion["letra"],
                opcion["texto"],
            ),
        )

def regenerar_banco(
    conn,
    convocatoria_id,
):

    eliminadas = vaciar_banco_convocatoria(
        conn,
        convocatoria_id,
    )

    evaluaciones = obtener_evaluaciones_aceptadas(
        conn,
        convocatoria_id,
    )

    insertadas = 0
    omitidas = 0

    for evaluacion in evaluaciones:

        opciones = obtener_opciones_importadas(
            conn,
            evaluacion["pregunta_importada_id"],
        )

        letras = {
            opcion["letra"]
            for opcion in opciones
        }

        if letras != {"A", "B", "C", "D"}:

            omitidas += 1
            continue

        banco_pregunta_id = insertar_banco_pregunta(
            conn,
            convocatoria_id,
            evaluacion,
        )

        insertar_banco_opciones(
            conn,
            banco_pregunta_id,
            opciones,
        )

        insertadas += 1

    return {
        "eliminadas": eliminadas,
        "aceptadas": len(evaluaciones),
        "insertadas": insertadas,
        "omitidas": omitidas,
    }

def main():

    argumentos = crear_argumentos()

    conn = abrir_conexion()

    try:

        convocatoria_id = obtener_convocatoria(
            conn,
            argumentos.codigo_cfg,
        )

        resumen = regenerar_banco(
            conn,
            convocatoria_id,
        )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()

    print()
    print("=" * 70)
    print("ACTUALIZACIÓN DEL BANCO")
    print("=" * 70)
    print(
        f"Convocatoria........: "
        f"{argumentos.codigo_cfg}"
    )
    print(
        f"Banco anterior......: "
        f"{resumen['eliminadas']}"
    )
    print(
        f"Evaluaciones aceptadas: "
        f"{resumen['aceptadas']}"
    )
    print(
        f"Insertadas..........: "
        f"{resumen['insertadas']}"
    )
    print(
        f"Omitidas............: "
        f"{resumen['omitidas']}"
    )
    print("=" * 70)


if __name__ == "__main__":

    main()