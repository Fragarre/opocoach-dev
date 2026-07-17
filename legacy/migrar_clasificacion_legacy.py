"""
Archivo: migrar_clasificacion_legacy.py
Ruta: procesos/migrar_clasificacion_legacy.py

Dependencias:
- argparse
- sqlite3
- pathlib
- core.temario

Funcionalidad:
Completa parte y tema en preguntas VALIDADA procedentes del proceso antiguo.

El script:

- selecciona preguntas VALIDADA con metodo_validacion vacío;
- utiliza norma_detectada y articulo_detectado;
- consulta Temario.obtener_temas_articulo();
- completa parte_detectada y tema_detectado cuando existe una única asociación;
- deja sin modificar los casos ambiguos o sin asociación;
- guarda únicamente cuando se utiliza --guardar.

No llama a BM25 ni a OpenAI.
Por defecto no modifica la base de datos.
"""

import argparse
import sqlite3
from collections import Counter
from pathlib import Path

from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Completa parte y tema en clasificaciones legacy."
        )
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help="Guarda los cambios en la base de datos.",
    )

    return parser.parse_args()


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            "No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    return conn


def cargar_preguntas_legacy(
    conn,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            examen_id,
            numero,
            norma_detectada,
            articulo_detectado,
            parte_detectada,
            tema_detectado,
            metodo_validacion,
            motivo_validacion
        FROM preguntas_importadas
        WHERE
            estado_validacion = 'VALIDADA'
            AND (
                metodo_validacion IS NULL
                OR TRIM(metodo_validacion) = ''
            )
            AND (
                parte_detectada IS NULL
                OR tema_detectado IS NULL
            )
        ORDER BY id
        """
    )

    return cur.fetchall()


def actualizar_pregunta(
    conn,
    pregunta_id,
    parte,
    tema,
):

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE preguntas_importadas
        SET
            parte_detectada = ?,
            tema_detectado = ?,
            metodo_validacion = 'LEGACY_TEMARIO'
        WHERE
            id = ?
            AND estado_validacion = 'VALIDADA'
        """,
        (
            parte,
            tema,
            pregunta_id,
        ),
    )

    if cur.rowcount != 1:

        raise RuntimeError(
            "No se pudo actualizar la pregunta "
            f"{pregunta_id}."
        )


def main():

    argumentos = crear_argumentos()

    conn = abrir_conexion()

    resumen = Counter()

    try:

        temario = Temario()

        preguntas = cargar_preguntas_legacy(
            conn
        )

        print()
        print("=" * 80)
        print("MIGRACIÓN DE CLASIFICACIONES LEGACY")
        print("=" * 80)
        print(
            f"Preguntas seleccionadas: "
            f"{len(preguntas)}"
        )
        print(
            f"Modo.................: "
            f"{'GUARDAR' if argumentos.guardar else 'PRUEBA'}"
        )

        for pregunta in preguntas:

            norma = pregunta[
                "norma_detectada"
            ]

            articulo = pregunta[
                "articulo_detectado"
            ]

            if not norma or not articulo:

                resumen[
                    "SIN_REFERENCIA"
                ] += 1

                continue

            temas = (
                temario.obtener_temas_articulo(
                    norma,
                    articulo,
                )
            )

            if len(temas) == 0:

                resumen[
                    "SIN_ASOCIACION"
                ] += 1

                continue

            if len(temas) > 1:

                resumen[
                    "AMBIGUA"
                ] += 1

                continue

            asociacion = temas[0]

            print()
            print(
                f"ID {pregunta['id']} "
                f"| {norma} "
                f"| art. {articulo}"
            )
            print(
                f"→ {asociacion['parte']} "
                f"| Tema {asociacion['tema']}"
            )

            resumen[
                "COMPLETADA"
            ] += 1

            if argumentos.guardar:

                actualizar_pregunta(
                    conn=conn,
                    pregunta_id=pregunta["id"],
                    parte=asociacion["parte"],
                    tema=asociacion["tema"],
                )

        if argumentos.guardar:

            conn.commit()

        else:

            conn.rollback()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(
        f"Completadas.........: "
        f"{resumen['COMPLETADA']}"
    )
    print(
        f"Ambiguas............: "
        f"{resumen['AMBIGUA']}"
    )
    print(
        f"Sin asociación......: "
        f"{resumen['SIN_ASOCIACION']}"
    )
    print(
        f"Sin referencia......: "
        f"{resumen['SIN_REFERENCIA']}"
    )

    if argumentos.guardar:

        print()
        print(
            "Cambios guardados correctamente."
        )

    else:

        print()
        print(
            "MODO PRUEBA: no se ha modificado "
            "la base de datos."
        )


if __name__ == "__main__":
    main()