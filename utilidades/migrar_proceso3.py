"""
Archivo: migrar_proceso3.py
Ruta: utilidades/migrar_proceso3.py

Dependencias:
- sqlite3
- pathlib

Funcionalidad:
Añade de forma idempotente a preguntas_importadas los campos necesarios
para el Proceso 3 de clasificación de preguntas.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path("db/oposiciones.sqlite3")


COLUMNAS = {
    "confianza_validacion": "REAL",
    "metodo_validacion": "TEXT",
    "tipo_pregunta": "TEXT",
}


def obtener_columnas(cursor, tabla):

    cursor.execute(
        f'PRAGMA table_info("{tabla}")'
    )

    return {
        fila[1]
        for fila in cursor.fetchall()
    }


def main():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: {DB_PATH.resolve()}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:

        cursor = conn.cursor()

        columnas_existentes = obtener_columnas(
            cursor,
            "preguntas_importadas",
        )

        añadidas = []
        existentes = []

        for nombre, tipo in COLUMNAS.items():

            if nombre in columnas_existentes:
                existentes.append(nombre)
                continue

            cursor.execute(
                f"""
                ALTER TABLE preguntas_importadas
                ADD COLUMN {nombre} {tipo}
                """
            )

            añadidas.append(nombre)

        conn.commit()

        print()
        print("=" * 70)
        print("MIGRACIÓN PROCESO 3")
        print("=" * 70)
        print(f"Base de datos: {DB_PATH.resolve()}")
        print()

        for nombre in existentes:
            print(f"YA EXISTE : {nombre}")

        for nombre in añadidas:
            print(f"AÑADIDA   : {nombre}")

        print()
        print(f"Columnas añadidas: {len(añadidas)}")
        print("=" * 70)

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


if __name__ == "__main__":
    main()