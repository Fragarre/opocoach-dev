"""
Archivo: obtener_fragmento.py
Ruta: core/obtener_fragmento.py

Obtiene el fragmento legal asociado a una pregunta.
"""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def obtener_fragmento(
    fragmento_id,
):

    if fragmento_id is None:
        return None

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute(
        """
        SELECT

            f.id,
            f.referencia,
            f.articulo,
            f.apartado,
            f.texto,

            d.nombre_archivo

        FROM fragmentos f

        JOIN documentos d
            ON d.id = f.documento_id

        WHERE
            f.id = ?
        """,
        (
            fragmento_id,
        ),
    )

    fila = cur.fetchone()

    conn.close()

    if fila is None:
        return None

    return dict(
        fila
    )