"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : obtener_fragmento.py
Ruta    : core/obtener_fragmento.py

Objetivo:
    Recuperar un fragmento normativo por su identificador.

Entradas:
    - Identificador de fragmento.

Salidas:
    - Texto y metadatos del fragmento.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_explicaciones.py

Flujo:
    1. Consulta SQLite.
    2. Devuelve el fragmento completo.

Observaciones:
    - Ninguna.

==============================================================================
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