"""
Archivo: selector_banco.py
Ruta: core/selector_banco.py

Selecciona preguntas completas del banco por:
- bloque del examen;
- tema.

Cada pregunta incluye:
- enunciado;
- opciones A, B, C y D;
- respuesta correcta;
- norma y artículo;
- origen;
- datos del examen.

Permite excluir preguntas ya utilizadas.

No modifica la base de datos.
"""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: {RUTA_BD}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    return conn


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

    letras_esperadas = {
        "A",
        "B",
        "C",
        "D",
    }

    if set(opciones) != letras_esperadas:

        raise ValueError(
            f"La pregunta {pregunta_id} no tiene "
            "exactamente las opciones A, B, C y D."
        )

    return opciones


def convertir_pregunta(
    conn,
    fila,
):

    opciones = cargar_opciones(
        conn=conn,
        pregunta_id=fila["id"],
    )

    respuesta_correcta = str(
        fila["respuesta_correcta"] or ""
    ).strip().upper()

    if respuesta_correcta not in opciones:

        raise ValueError(
            f"La pregunta {fila['id']} tiene una "
            "respuesta correcta no válida: "
            f"{respuesta_correcta}"
        )

    return {
        "id": fila["id"],
        "examen_id": fila["examen_id"],
        "numero_original": fila["numero"],
        "numero_simulacro": None,

        "tipo_examen": fila["tipo_examen"],
        "nombre_archivo": fila["nombre_archivo"],
        "origen": "BANCO",

        "tipo_pregunta": fila["tipo_pregunta"],
        "parte": fila["parte_detectada"],
        "tema": fila["tema_detectado"],

        "enunciado": fila["enunciado"],
        "opciones": opciones,
        "respuesta_correcta": respuesta_correcta,
        "texto_respuesta_correcta": opciones[
            respuesta_correcta
        ],

        "norma": fila["norma_detectada"],
        "articulo": fila["articulo_detectado"],
        "fragmento_id": fila["fragmento_id"],
    }


def seleccionar_preguntas(
    tipo_pregunta,
    tema,
    cantidad,
    excluidas=None,
):

    if cantidad <= 0:

        return {
            "preguntas": [],
            "obtenidas": 0,
            "solicitadas": cantidad,
            "faltan": 0,
        }

    if excluidas is None:

        excluidas = set()

    conn = abrir_conexion()

    try:

        sql = """
            SELECT
                pi.id,
                pi.examen_id,
                pi.numero,

                pi.tipo_pregunta,
                pi.parte_detectada,
                pi.tema_detectado,

                pi.enunciado,
                pi.respuesta_correcta,

                pi.norma_detectada,
                pi.articulo_detectado,

                pi.fragmento_detectado_id AS fragmento_id,

                e.tipo_examen,
                e.nombre_archivo

            FROM preguntas_importadas pi

            JOIN examenes e
                ON e.id = pi.examen_id

            WHERE
                pi.estado_validacion = 'VALIDADA'

                AND pi.tipo_pregunta = ?

                AND pi.tema_detectado = ?

                AND e.tipo_examen IN (
                    'MODELO',
                    'APOYO'
                )
        """

        parametros = [
            tipo_pregunta,
            tema,
        ]

        if excluidas:

            marcadores = ",".join(
                "?"
                for _ in excluidas
            )

            sql += f"""
                AND pi.id NOT IN (
                    {marcadores}
                )
            """

            parametros.extend(
                sorted(excluidas)
            )

        sql += """
            ORDER BY RANDOM()
            LIMIT ?
        """

        parametros.append(
            cantidad
        )

        cur = conn.cursor()

        cur.execute(
            sql,
            parametros,
        )

        filas = cur.fetchall()

        preguntas = [
            convertir_pregunta(
                conn=conn,
                fila=fila,
            )
            for fila in filas
        ]

        obtenidas = len(
            preguntas
        )

        return {
            "preguntas": preguntas,
            "obtenidas": obtenidas,
            "solicitadas": cantidad,
            "faltan": max(
                0,
                cantidad - obtenidas,
            ),
        }

    finally:

        conn.close()


def prueba():

    resultado = seleccionar_preguntas(
        tipo_pregunta="GENERAL",
        tema=1,
        cantidad=5,
    )

    print()
    print("=" * 80)
    print("PRUEBA SELECTOR BANCO")
    print("=" * 80)

    print(
        f"Solicitadas....: "
        f"{resultado['solicitadas']}"
    )

    print(
        f"Obtenidas......: "
        f"{resultado['obtenidas']}"
    )

    print(
        f"Faltan.........: "
        f"{resultado['faltan']}"
    )

    for pregunta in resultado["preguntas"]:

        print()
        print(
            f"ID.............: {pregunta['id']}"
        )
        print(
            f"Origen.........: {pregunta['origen']}"
        )
        print(
            f"Examen.........: {pregunta['tipo_examen']}"
        )
        print(
            f"Bloque.........: {pregunta['tipo_pregunta']}"
        )
        print(
            f"Tema...........: {pregunta['tema']}"
        )
        print(
            f"Norma..........: {pregunta['norma']}"
        )
        print(
            f"Artículo.......: {pregunta['articulo']}"
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

            marca = (
                "  <- CORRECTA"
                if letra
                == pregunta["respuesta_correcta"]
                else ""
            )

            print(
                f"{letra}) "
                f"{pregunta['opciones'][letra]}"
                f"{marca}"
            )


if __name__ == "__main__":

    prueba()