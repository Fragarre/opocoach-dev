"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : clasificar_pendientes.py
Ruta    : procesos/clasificar_pendientes.py

Objetivo:
    Clasificar en lote preguntas pendientes de validación.

Entradas:
    - Preguntas pendientes.
    - Temario de la convocatoria.

Salidas:
    - Estados y clasificación temática actualizados.

Modifica BD:
    Sí

Tablas afectadas:
    - preguntas_importadas

Utiliza:
    - core.clasificador
    - core.temario

Utilizado por:
    - Ninguna.

Flujo:
    1. Carga pendientes.
    2. Clasifica.
    3. Muestra resultados.
    4. Guarda opcionalmente.

Observaciones:
    - Ninguna.

==============================================================================
"""
import argparse
import sqlite3
from collections import Counter
from pathlib import Path

from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Clasifica preguntas importadas pendientes."
        )
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help=(
            "Número máximo de preguntas a procesar. "
            "Valor por defecto: 5."
        ),
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help=(
            "Guarda los resultados en la base de datos."
        ),
    )

    parser.add_argument(
        "--modelo",
        default="gpt-5.4-mini",
        help=(
            "Modelo utilizado en las clasificaciones "
            "asistidas por IA."
        ),
    )

    parser.add_argument(
        "--limite-fragmentos",
        type=int,
        default=5,
        help=(
            "Número máximo de candidatos enviados "
            "a la IA."
        ),
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


def cargar_pendientes(
    conn,
    limite,
):

    cur = conn.cursor()

    if limite is None:

        cur.execute(
            """
            SELECT
                id,
                examen_id,
                numero,
                enunciado,
                respuesta_correcta,
                parte_detectada,
                tipo_pregunta
            FROM preguntas_importadas
            WHERE estado_validacion = 'PENDIENTE'
            ORDER BY id
            """
        )

    else:

        cur.execute(
            """
            SELECT
                id,
                examen_id,
                numero,
                enunciado,
                respuesta_correcta,
                parte_detectada,
                tipo_pregunta
            FROM preguntas_importadas
            WHERE estado_validacion = 'PENDIENTE'
            ORDER BY id
            LIMIT ?
            """,
            (limite,),
        )
    return cur.fetchall()


def cargar_opciones(
    conn,
    pregunta_id,
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
            pregunta_id,
        ),
    )

    opciones = {
        fila["letra"].strip().upper(): fila["texto"]
        for fila in cur.fetchall()
    }

    if set(opciones) != {
        "A",
        "B",
        "C",
        "D",
    }:

        raise ValueError(
            "La pregunta "
            f"{pregunta_id} no tiene exactamente "
            "las opciones A, B, C y D."
        )

    return opciones


def guardar_resultado(
    conn,
    pregunta_id,
    resultado,
):

    if resultado["estado"] not in {
        "VALIDADA",
        "A_REVISAR",
        "RECHAZADA",
    }:

        raise ValueError(
            "Estado de clasificación no definitivo: "
            f"{resultado['estado']}"
        )

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE preguntas_importadas
        SET
            parte_detectada = ?,
            tema_detectado = ?,
            estado_validacion = ?,
            fragmento_detectado_id = ?,
            motivo_validacion = ?,
            norma_detectada = ?,
            articulo_detectado = ?,
            confianza_validacion = ?,
            metodo_validacion = ?
        WHERE
            id = ?
            AND estado_validacion = 'PENDIENTE'
        """,
        (
            resultado["parte"],
            resultado["tema"],
            resultado["estado"],
            resultado["fragmento_id"],
            resultado["motivo"],
            resultado["norma"],
            resultado["articulo"],
            resultado["confianza"],
            resultado["metodo_validacion"],
            pregunta_id,
        ),
    )

    if cur.rowcount != 1:

        raise RuntimeError(
            "No se pudo actualizar la pregunta "
            f"{pregunta_id}."
        )


def mostrar_resultado(
    pregunta,
    resultado,
):

    print()
    print("=" * 80)
    print(
        f"Pregunta ID {pregunta['id']} "
        f"| Examen {pregunta['examen_id']} "
        f"| Número {pregunta['numero']}"
    )
    print("=" * 80)
    print(
        pregunta["enunciado"]
    )
    print("-" * 80)
    print(
        f"Estado............: "
        f"{resultado['estado']}"
    )
    print(
        f"Norma.............: "
        f"{resultado['norma']}"
    )
    print(
        f"Artículo..........: "
        f"{resultado['articulo']}"
    )
    print(
        f"Parte.............: "
        f"{resultado['parte']}"
    )
    print(
        f"Tema..............: "
        f"{resultado['tema']}"
    )
    print(
        f"Documento.........: "
        f"{resultado['documento']}"
    )
    print(
        f"Fragmento.........: "
        f"{resultado['fragmento_id']}"
    )
    print(
        f"Confianza.........: "
        f"{resultado['confianza']}"
    )
    print(
        f"Método............: "
        f"{resultado['metodo_validacion']}"
    )
    print(
        f"Motivo............: "
        f"{resultado['motivo']}"
    )


def main():

    argumentos = crear_argumentos()

    if (
        argumentos.limite is not None
        and argumentos.limite < 1
    ):

        raise ValueError(
            "--limite debe ser mayor que cero."
        )
    
    if argumentos.limite_fragmentos < 1:

        raise ValueError(
            "--limite-fragmentos debe ser "
            "mayor que cero."
        )

    conn = abrir_conexion()

    resultados_estado = Counter()
    resultados_metodo = Counter()
    procesadas = 0

    try:

        preguntas = cargar_pendientes(
            conn=conn,
            limite=argumentos.limite,
        )

        if not preguntas:

            print(
                "No existen preguntas pendientes."
            )
            return

        temario = Temario()

        clasificador = Clasificador(
            temario
        )

        print()
        print("=" * 80)
        print("CLASIFICACIÓN DE PREGUNTAS PENDIENTES")
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

            respuesta_correcta = str(
                pregunta["respuesta_correcta"] or ""
            ).strip().upper()

            if respuesta_correcta not in {
                "A",
                "B",
                "C",
                "D",
            }:

                raise ValueError(
                    "La pregunta "
                    f"{pregunta['id']} no tiene una "
                    "respuesta correcta válida."
                )

            opciones = cargar_opciones(
                conn=conn,
                pregunta_id=pregunta["id"],
            )

            resultado = clasificador.clasificar(
                conn=conn,
                pregunta=pregunta["enunciado"],
                opciones=opciones,
                respuesta_correcta=respuesta_correcta,
                limite_fragmentos=(
                    argumentos.limite_fragmentos
                ),
                modelo=argumentos.modelo,
                parte_origen=(
                    pregunta["parte_detectada"]
                ),
            )

            mostrar_resultado(
                pregunta=pregunta,
                resultado=resultado,
            )

            resultados_estado[
                resultado["estado"]
            ] += 1

            resultados_metodo[
                resultado["metodo_validacion"]
            ] += 1

            procesadas += 1

            if argumentos.guardar:

                guardar_resultado(
                    conn=conn,
                    pregunta_id=pregunta["id"],
                    resultado=resultado,
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
        f"Procesadas..........: "
        f"{procesadas}"
    )

    for estado in (
        "VALIDADA",
        "A_REVISAR",
        "RECHAZADA",
    ):

        print(
            f"{estado:<20}: "
            f"{resultados_estado[estado]}"
        )

    print()
    print("Métodos:")

    for metodo, cantidad in sorted(
        resultados_metodo.items()
    ):

        print(
            f"- {metodo}: {cantidad}"
        )

    print()

    if argumentos.guardar:

        print(
            "Resultados guardados correctamente."
        )

    else:

        print(
            "MODO PRUEBA: no se ha modificado "
            "la base de datos."
        )


if __name__ == "__main__":
    main()