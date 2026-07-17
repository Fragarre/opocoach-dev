"""
Archivo:
core/distribucion_modelo.py
"""

import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

def obtener_distribucion_modelo():

    OBJETIVOS = {
        "ESPECIAL_TEORIA": 50,
        "ESPECIAL_PRACTICA": 15,
        "ESPECIAL_INFORMATICA": 15,
        "GENERAL": 30,
    }

    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pi.tipo_pregunta,
            pi.tema_detectado,
            COUNT(*) total
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

    real = defaultdict(dict)

    for fila in cur.fetchall():

        real[
            fila["tipo_pregunta"]
        ][
            fila["tema_detectado"]
        ] = fila["total"]

    conn.close()

    ajustada = {}

    for bloque, temas in real.items():

        objetivo = OBJETIVOS[bloque]

        total_real = sum(
            temas.values()
        )

        if total_real == objetivo:

            ajustada[bloque] = dict(temas)
            continue

        cuotas = {}

        resultado = {}

        for tema, cantidad in temas.items():

            cuota = (
                cantidad
                * objetivo
                / total_real
            )

            cuotas[tema] = cuota

            resultado[tema] = int(cuota)

        faltan = (
            objetivo
            - sum(resultado.values())
        )

        if faltan > 0:

            residuos = sorted(
                temas.keys(),
                key=lambda t: (
                    cuotas[t]
                    - resultado[t]
                ),
                reverse=True,
            )

            for tema in residuos[:faltan]:

                resultado[tema] += 1

        ajustada[bloque] = resultado

    return ajustada


