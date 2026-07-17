"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : migrar_banco_actual.py
Ruta    : procesos/migrar_banco_actual.py

Objetivo:
    Incorporar al banco de la convocatoria actual las preguntas importadas
    que ya están validadas y clasificadas.

Entradas:
    - preguntas_importadas con estado_validacion = VALIDADA.
    - Convocatoria C1-01_58_26.

Salidas:
    - banco_preguntas.
    - banco_opciones.

Modifica BD:
    Sí

Tablas afectadas:
    - banco_preguntas
    - banco_opciones

Utiliza:
    - sqlite3
    - pathlib

Utilizado por:
    - Ejecución manual.

Flujo:
    1. Localiza la convocatoria destino.
    2. Recupera preguntas validadas y clasificadas.
    3. Resuelve parte_id y tema_id.
    4. Inserta la pregunta de forma idempotente.
    5. Copia sus opciones.

Observaciones:
    - No incorpora A_REVISAR ni RECHAZADA.
    - Puede ejecutarse varias veces sin duplicar preguntas.

==============================================================================
"""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

CODIGO_CFG = "C1-01_58_26"


def abrir_conexion():

    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def obtener_convocatoria_id(conn):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (CODIGO_CFG,),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            f"No existe la convocatoria {CODIGO_CFG}"
        )

    return fila["id"]


def obtener_preguntas(conn):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pi.id,
            pi.enunciado,
            pi.respuesta_correcta,
            pi.parte_detectada,
            pi.tema_detectado,
            pi.fragmento_detectado_id
        FROM preguntas_importadas pi
        WHERE pi.estado_validacion = 'VALIDADA'
          AND pi.parte_detectada IS NOT NULL
          AND pi.tema_detectado IS NOT NULL
          AND pi.respuesta_correcta IN ('A', 'B', 'C', 'D')
        ORDER BY pi.id
        """
    )

    return cur.fetchall()


def obtener_parte_id(
    conn,
    convocatoria_id,
    nombre_parte,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM partes_temario
        WHERE convocatoria_id = ?
          AND nombre = ?
        """,
        (
            convocatoria_id,
            nombre_parte,
        ),
    )

    fila = cur.fetchone()

    return fila["id"] if fila else None


def obtener_tema_id(
    conn,
    convocatoria_id,
    parte_id,
    numero_tema,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM temas
        WHERE convocatoria_id = ?
          AND parte_id = ?
          AND numero = ?
        """,
        (
            convocatoria_id,
            parte_id,
            numero_tema,
        ),
    )

    fila = cur.fetchone()

    return fila["id"] if fila else None


def obtener_opciones(
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


def insertar_pregunta(
    conn,
    convocatoria_id,
    parte_id,
    tema_id,
    pregunta,
):

    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO banco_preguntas (
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
            pregunta["id"],
            convocatoria_id,
            parte_id,
            tema_id,
            pregunta["fragmento_detectado_id"],
            pregunta["enunciado"],
            pregunta["respuesta_correcta"],
        ),
    )

    if cur.rowcount == 1:

        return cur.lastrowid, True

    cur.execute(
        """
        SELECT id
        FROM banco_preguntas
        WHERE convocatoria_id = ?
          AND pregunta_importada_id = ?
        """,
        (
            convocatoria_id,
            pregunta["id"],
        ),
    )

    fila = cur.fetchone()

    return fila["id"], False


def insertar_opciones(
    conn,
    banco_pregunta_id,
    opciones,
):

    cur = conn.cursor()

    for opcion in opciones:

        cur.execute(
            """
            INSERT OR IGNORE INTO banco_opciones (
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


def main():

    conn = abrir_conexion()

    try:

        convocatoria_id = obtener_convocatoria_id(
            conn
        )

        preguntas = obtener_preguntas(
            conn
        )

        insertadas = 0
        existentes = 0
        omitidas = 0

        for pregunta in preguntas:

            parte_id = obtener_parte_id(
                conn=conn,
                convocatoria_id=convocatoria_id,
                nombre_parte=pregunta["parte_detectada"],
            )

            if parte_id is None:

                omitidas += 1
                continue

            tema_id = obtener_tema_id(
                conn=conn,
                convocatoria_id=convocatoria_id,
                parte_id=parte_id,
                numero_tema=pregunta["tema_detectado"],
            )

            if tema_id is None:

                omitidas += 1
                continue

            opciones = obtener_opciones(
                conn=conn,
                pregunta_importada_id=pregunta["id"],
            )

            if len(opciones) != 4:

                omitidas += 1
                continue

            banco_pregunta_id, nueva = insertar_pregunta(
                conn=conn,
                convocatoria_id=convocatoria_id,
                parte_id=parte_id,
                tema_id=tema_id,
                pregunta=pregunta,
            )

            insertar_opciones(
                conn=conn,
                banco_pregunta_id=banco_pregunta_id,
                opciones=opciones,
            )

            if nueva:
                insertadas += 1
            else:
                existentes += 1

        conn.commit()

    finally:

        conn.close()

    print()
    print("=" * 70)
    print("MIGRACIÓN DEL BANCO ACTUAL")
    print("=" * 70)
    print(f"Preguntas candidatas....: {len(preguntas)}")
    print(f"Insertadas...............: {insertadas}")
    print(f"Ya existentes...........: {existentes}")
    print(f"Omitidas................: {omitidas}")
    print("=" * 70)


if __name__ == "__main__":

    main()