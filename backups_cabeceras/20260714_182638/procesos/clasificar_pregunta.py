"""
Archivo: clasificar_pregunta.py
Ruta: procesos/clasificar_pregunta.py

Dependencias:
- argparse
- sqlite3
- pathlib
- core.temario
- core.clasificador

Funcionalidad:
Clasifica una única pregunta importada mediante el Proceso 3.

El script:

- lee la pregunta y sus cuatro opciones desde la base de datos;
- ejecuta core.clasificador.Clasificador;
- muestra el resultado completo;
- guarda el resultado únicamente cuando se utiliza --guardar.

No contiene lógica propia de:

- detección de normas;
- detección de artículos;
- búsqueda BM25;
- construcción de prompts;
- comunicación con OpenAI;
- asignación de parte o tema.

Toda la clasificación se delega en core.clasificador.

Por defecto no modifica la base de datos.

Con la opción --guardar actualiza exclusivamente la pregunta indicada.
"""

import argparse
import sqlite3
from pathlib import Path

from core.clasificador import Clasificador
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Clasifica una pregunta importada "
            "mediante el Proceso 3."
        )
    )

    parser.add_argument(
        "pregunta_id",
        type=int,
        help=(
            "Identificador de la pregunta "
            "en preguntas_importadas."
        ),
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help=(
            "Guarda el resultado en la base de datos."
        ),
    )

    parser.add_argument(
        "--modelo",
        default="gpt-5.4-mini",
        help=(
            "Modelo de OpenAI utilizado en las "
            "clasificaciones asistidas."
        ),
    )

    parser.add_argument(
        "--limite-fragmentos",
        type=int,
        default=5,
        help=(
            "Número máximo de fragmentos candidatos "
            "enviados a la IA."
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


def cargar_pregunta(
    conn,
    pregunta_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            examen_id,
            numero,
            enunciado,
            respuesta_correcta,
            parte_detectada,
            tema_detectado,
            estado_importacion,
            estado_validacion,
            fragmento_detectado_id,
            motivo_validacion,
            norma_detectada,
            articulo_detectado,
            confianza_validacion,
            metodo_validacion,
            tipo_pregunta
        FROM preguntas_importadas
        WHERE id = ?
        """,
        (
            pregunta_id,
        ),
    )

    pregunta = cur.fetchone()

    if pregunta is None:

        raise ValueError(
            "No existe la pregunta importada "
            f"con id {pregunta_id}."
        )

    return pregunta


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

    filas = cur.fetchall()

    opciones = {
        fila["letra"].strip().upper(): fila["texto"]
        for fila in filas
    }

    letras_esperadas = {
        "A",
        "B",
        "C",
        "D",
    }

    if set(opciones) != letras_esperadas:

        raise ValueError(
            "La pregunta debe tener exactamente "
            "las opciones A, B, C y D. "
            f"Opciones encontradas: "
            f"{sorted(opciones)}"
        )

    return opciones


def validar_pregunta(
    pregunta,
):

    if pregunta[
        "estado_validacion"
    ] != "PENDIENTE":

        raise ValueError(
            "La pregunta no está pendiente. "
            "Estado actual: "
            f"{pregunta['estado_validacion']}"
        )

    respuesta = str(
        pregunta["respuesta_correcta"] or ""
    ).strip().upper()

    if respuesta not in {
        "A",
        "B",
        "C",
        "D",
    }:

        raise ValueError(
            "La pregunta no contiene una respuesta "
            "correcta válida."
        )

    # parte = str(
    #     pregunta["parte_detectada"] or ""
    # ).lower()

    # if "informática" in parte or "informatica" in parte:

    #     raise ValueError(
    #         "La rama de Informática todavía no está "
    #         "integrada en Clasificador. La pregunta "
    #         "no se procesará mediante la rama normativa."
    #     )


def mostrar_pregunta(
    pregunta,
    opciones,
):

    print()
    print("=" * 80)
    print("PREGUNTA IMPORTADA")
    print("=" * 80)
    print(
        f"ID................: "
        f"{pregunta['id']}"
    )
    print(
        f"Examen............: "
        f"{pregunta['examen_id']}"
    )
    print(
        f"Número............: "
        f"{pregunta['numero']}"
    )
    print(
        f"Estado actual.....: "
        f"{pregunta['estado_validacion']}"
    )
    print()
    print(
        pregunta["enunciado"]
    )
    print()

    for letra in (
        "A",
        "B",
        "C",
        "D",
    ):

        indicador = (
            "  ← CORRECTA"
            if letra
            == pregunta["respuesta_correcta"].upper()
            else ""
        )

        print(
            f"{letra}) {opciones[letra]}"
            f"{indicador}"
        )


def mostrar_resultado(
    resultado,
):

    print()
    print("=" * 80)
    print("RESULTADO DE CLASIFICACIÓN")
    print("=" * 80)
    print(
        f"Resuelta..........: "
        f"{resultado['resuelta']}"
    )
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

    temas = resultado[
        "temas_compatibles"
    ]

    if temas:

        print()
        print("Temas compatibles:")

        for tema in temas:

            print(
                f"- {tema['parte']} / "
                f"Tema {tema['tema']} / "
                f"{tema.get('titulo', '')}"
            )


def guardar_resultado(
    conn,
    pregunta_id,
    resultado,
):

    estados_permitidos = {
        "VALIDADA",
        "A_REVISAR",
        "RECHAZADA",
    }

    if resultado[
        "estado"
    ] not in estados_permitidos:

        raise ValueError(
            "No se puede guardar un resultado "
            "que no sea definitivo."
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

        conn.rollback()

        raise RuntimeError(
            "No se ha actualizado la pregunta. "
            "Puede haber cambiado su estado durante "
            "la ejecución."
        )

    conn.commit()


def main():

    argumentos = crear_argumentos()

    if argumentos.limite_fragmentos < 1:

        raise ValueError(
            "--limite-fragmentos debe ser "
            "mayor que cero."
        )

    conn = abrir_conexion()

    try:

        pregunta = cargar_pregunta(
            conn=conn,
            pregunta_id=argumentos.pregunta_id,
        )

        validar_pregunta(
            pregunta
        )

        opciones = cargar_opciones(
            conn=conn,
            pregunta_id=pregunta["id"],
        )

        mostrar_pregunta(
            pregunta=pregunta,
            opciones=opciones,
        )

        temario = Temario()

        clasificador = Clasificador(
            temario
        )

        resultado = clasificador.clasificar(
            conn=conn,
            pregunta=pregunta["enunciado"],
            opciones=opciones,
            respuesta_correcta=(
                pregunta["respuesta_correcta"]
            ),
            limite_fragmentos=(
                argumentos.limite_fragmentos
            ),
            modelo=argumentos.modelo,
            parte_origen=pregunta["parte_detectada"],
        )

        mostrar_resultado(
            resultado
        )

        if argumentos.guardar:

            guardar_resultado(
                conn=conn,
                pregunta_id=pregunta["id"],
                resultado=resultado,
            )

            print()
            print(
                "Resultado guardado correctamente."
            )

        else:

            print()
            print(
                "MODO PRUEBA: no se ha modificado "
                "la base de datos."
            )
            print(
                "Para guardar el resultado, utiliza "
                "la opción --guardar."
            )

    finally:

        conn.close()


if __name__ == "__main__":
    main()