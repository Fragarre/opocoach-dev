"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : calcular_distribucion_modelo.py
Ruta    : procesos/calcular_distribucion_modelo.py

Objetivo:
    Calcular la distribución del examen modelo por tipo y tema.

Entradas:
    - Preguntas clasificadas del examen modelo.

Salidas:
    - Resumen de distribución reutilizable.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - Ninguna.

Flujo:
    1. Consulta preguntas.
    2. Agrupa por tipo y tema.
    3. Muestra el resultado.

Observaciones:
    - Ninguna.

==============================================================================
"""
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def main():

    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pi.tipo_pregunta,
            pi.tema_detectado,
            COUNT(*) AS total
        FROM preguntas_importadas pi
        JOIN examenes e
            ON pi.examen_id = e.id
        WHERE
            e.tipo_examen='MODELO'
            AND pi.estado_validacion='VALIDADA'
        GROUP BY
            pi.tipo_pregunta,
            pi.tema_detectado
        ORDER BY
            pi.tipo_pregunta,
            pi.tema_detectado
        """
    )

    datos = defaultdict(dict)

    for fila in cur.fetchall():

        datos[
            fila["tipo_pregunta"]
        ][
            fila["tema_detectado"]
        ] = fila["total"]

    conn.close()

    for bloque in (
        "ESPECIAL_TEORIA",
        "ESPECIAL_PRACTICA",
        "ESPECIAL_INFORMATICA",
        "GENERAL",
    ):

        print()
        print("=" * 70)
        print(bloque)
        print("=" * 70)

        total = 0

        for tema, cantidad in sorted(
            datos[bloque].items()
        ):

            print(
                f"Tema {tema:>2} -> {cantidad}"
            )

            total += cantidad

        print("-" * 70)
        print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()