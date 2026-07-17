"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : buscar_explicacion.py
Ruta    : core/buscar_explicacion.py

Objetivo:
    Recuperar una explicación existente mediante la huella de la pregunta.

Entradas:
    - Huella de la pregunta.
    - Conexión SQLite.

Salidas:
    - Explicación reutilizable o None.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_explicaciones.py

Flujo:
    1. Consulta la tabla de explicaciones.
    2. Devuelve la coincidencia encontrada.

Observaciones:
    - Ninguna.

==============================================================================
"""
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def buscar_explicacion(
    huella,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute(
        """
        SELECT

            explicacion_breve,
            explicacion_extensa

        FROM explicaciones_preguntas

        WHERE
            huella_pregunta = ?
        """,
        (
            huella,
        ),
    )

    fila = cur.fetchone()

    conn.close()

    if fila is None:

        return None

    return {
    "breve": fila["explicacion_breve"],
    "extensa": fila["explicacion_extensa"],
    }