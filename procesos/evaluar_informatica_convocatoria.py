"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : EN DESARROLLO

Archivo : evaluar_informatica_convocatoria.py
Ruta    : procesos/evaluar_informatica_convocatoria.py

Objetivo:
    Evaluar preguntas de informática para una convocatoria concreta.

Entradas:
    - Preguntas importadas con materia_detectada.

Salidas:
    - evaluaciones_preguntas_convocatoria.

Modifica BD:
    Sí

Observaciones:
    - Es idempotente.
    - No modifica preguntas_importadas.
    - No actualiza directamente banco_preguntas.

==============================================================================
"""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

CODIGO_CFG = "C1-01_58_26"

MAPA_MATERIAS = {
    "INFORMATICA_BASICA": 15,
    "WINDOWS_11": 16,
    "EXPLORADOR_WINDOWS_11": 17,
    "OUTLOOK_365": 18,
    "WORD_365": 19,
    "EXCEL_365": 20,
    "TEAMS_365": 21,
    "NAVEGADORES_WEB": 22,
    "INTELIGENCIA_ARTIFICIAL": 23,
}

def abrir_conexion() -> sqlite3.Connection:

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn

def obtener_convocatoria_id(
    conn: sqlite3.Connection,
) -> int:

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

    return int(fila["id"])

def obtener_parte_informatica_id(
    conn: sqlite3.Connection,
    convocatoria_id: int,
) -> int:

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM partes_temario
        WHERE convocatoria_id = ?
          AND nombre = 'Especial-Informática'
        """,
        (convocatoria_id,),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            "No existe la parte Especial-Informática."
        )

    return int(fila["id"])

def obtener_preguntas_informatica(
    conn: sqlite3.Connection,
) -> list[sqlite3.Row]:

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            materia_detectada,
            respuesta_correcta
        FROM preguntas_importadas
        WHERE materia_detectada IS NOT NULL
        ORDER BY id
        """
    )

    return cur.fetchall()

def obtener_tema_id(
    conn: sqlite3.Connection,
    convocatoria_id: int,
    parte_id: int,
    numero_tema: int,
) -> int | None:

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

    if fila is None:
        return None

    return int(fila["id"])

def guardar_evaluacion(
    conn: sqlite3.Connection,
    pregunta_id: int,
    convocatoria_id: int,
    parte_id: int,
    tema_id: int | None,
    respuesta_correcta: str | None,
    materia: str,
) -> str:

    decision = (
        "ACEPTADA"
        if (
            tema_id is not None
            and respuesta_correcta in {
                "A",
                "B",
                "C",
                "D",
            }
        )
        else "A_REVISAR"
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO evaluaciones_preguntas_convocatoria (
            pregunta_importada_id,
            convocatoria_id,
            decision,
            parte_id,
            tema_id,
            tipo_pregunta,
            fragmento_id,
            motivo,
            confianza,
            metodo
        )
        VALUES (?, ?, ?, ?, ?, 'ESPECIAL_INFORMATICA',
                NULL, ?, NULL, 'MATERIA_INFORMATICA')
        ON CONFLICT (
            pregunta_importada_id,
            convocatoria_id
        )
        DO UPDATE SET
            decision = excluded.decision,
            parte_id = excluded.parte_id,
            tema_id = excluded.tema_id,
            tipo_pregunta = excluded.tipo_pregunta,
            fragmento_id = excluded.fragmento_id,
            motivo = excluded.motivo,
            confianza = excluded.confianza,
            metodo = excluded.metodo,
            fecha_evaluacion = CURRENT_TIMESTAMP
        """,
        (
            pregunta_id,
            convocatoria_id,
            decision,
            parte_id if decision == "ACEPTADA" else None,
            tema_id if decision == "ACEPTADA" else None,
            (
                f"Materia {materia} vinculada al tema."
                if decision == "ACEPTADA"
                else (
                    "No puede incorporarse automáticamente: "
                    "falta tema válido o respuesta correcta."
                )
            ),
        ),
    )

    return decision

def main():

    conn = abrir_conexion()

    try:

        convocatoria_id = obtener_convocatoria_id(
            conn
        )

        parte_id = obtener_parte_informatica_id(
            conn,
            convocatoria_id,
        )

        preguntas = obtener_preguntas_informatica(
            conn
        )

        aceptadas = 0
        revisar = 0

        for pregunta in preguntas:

            materia = pregunta[
                "materia_detectada"
            ]

            numero_tema = MAPA_MATERIAS.get(
                materia
            )

            tema_id = None

            if numero_tema is not None:

                tema_id = obtener_tema_id(
                    conn=conn,
                    convocatoria_id=convocatoria_id,
                    parte_id=parte_id,
                    numero_tema=numero_tema,
                )

            decision = guardar_evaluacion(
                conn=conn,
                pregunta_id=pregunta["id"],
                convocatoria_id=convocatoria_id,
                parte_id=parte_id,
                tema_id=tema_id,
                respuesta_correcta=pregunta[
                    "respuesta_correcta"
                ],
                materia=materia,
            )

            if decision == "ACEPTADA":
                aceptadas += 1
            else:
                revisar += 1

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    print()
    print("=" * 70)
    print("EVALUACIÓN INFORMÁTICA")
    print("=" * 70)
    print(f"Preguntas..........: {len(preguntas)}")
    print(f"Aceptadas..........: {aceptadas}")
    print(f"A revisar..........: {revisar}")
    print("=" * 70)


if __name__ == "__main__":

    main()

