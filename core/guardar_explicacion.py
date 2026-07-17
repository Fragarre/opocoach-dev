"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : guardar_explicacion.py
Ruta    : core/guardar_explicacion.py

Objetivo:
    Guardar una explicación generada o reutilizada para una pregunta.

Entradas:
    - Huella.
    - Explicación.
    - Metadatos de origen.

Salidas:
    - Registro persistido en SQLite.

Modifica BD:
    Sí

Tablas afectadas:
    - explicaciones_preguntas

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_explicaciones.py

Flujo:
    1. Comprueba la huella.
    2. Inserta o actualiza la explicación.

Observaciones:
    - Ninguna.

==============================================================================
"""
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def guardar_explicacion(
    pregunta_importada_id,
    huella,
    breve,
    extensa,
    modelo,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO explicaciones_preguntas (
                pregunta_importada_id,
                huella_pregunta,
                explicacion_breve,
                explicacion_extensa,
                modelo_ia
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(huella_pregunta)
            DO UPDATE SET
                pregunta_importada_id =
                    excluded.pregunta_importada_id,
                explicacion_breve =
                    excluded.explicacion_breve,
                explicacion_extensa =
                    excluded.explicacion_extensa,
                modelo_ia =
                    excluded.modelo_ia,
                fecha_generacion =
                    CURRENT_TIMESTAMP
            """,
            (
                pregunta_importada_id,
                huella,
                breve,
                extensa,
                modelo,
            ),
        )

        conn.commit()

    finally:

        conn.close()