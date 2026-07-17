"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : selector_banco.py
Ruta    : core/selector_banco.py

Objetivo:
    Seleccionar preguntas aceptadas del banco de una convocatoria por tipo
    de pregunta y tema.

Entradas:
    - Código CFG de convocatoria.
    - Tipo de pregunta.
    - Número de tema.
    - Cantidad.
    - IDs de banco excluidos.

Salidas:
    - Preguntas completas.
    - Número de preguntas obtenidas y faltantes.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - sqlite3
    - pathlib

Utilizado por:
    - core/constructor_simulacro.py

Flujo:
    1. Localiza la convocatoria.
    2. Filtra preguntas aceptadas del banco.
    3. Filtra por tipo y tema.
    4. Excluye preguntas ya utilizadas.
    5. Recupera opciones y metadatos.

Observaciones:
    - Nunca selecciona directamente desde preguntas_importadas.
    - Solo utiliza registros VALIDADA de banco_preguntas.

==============================================================================
"""

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

CODIGO_CFG_DEFAULT = "C1-01_58_26"


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: {RUTA_BD}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def obtener_convocatoria_id(
    conn,
    codigo_cfg,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (
            codigo_cfg,
        ),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            "No existe la convocatoria "
            f"{codigo_cfg!r}."
        )

    return fila["id"]


def cargar_opciones(
    conn,
    banco_pregunta_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            letra,
            texto
        FROM banco_opciones
        WHERE banco_pregunta_id = ?
        ORDER BY letra
        """,
        (
            banco_pregunta_id,
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
            "La pregunta de banco "
            f"{banco_pregunta_id} no tiene "
            "exactamente las opciones A, B, C y D."
        )

    return opciones


def convertir_pregunta(
    conn,
    fila,
):

    opciones = cargar_opciones(
        conn=conn,
        banco_pregunta_id=fila["banco_pregunta_id"],
    )

    respuesta_correcta = str(
        fila["respuesta_correcta"] or ""
    ).strip().upper()

    if respuesta_correcta not in opciones:

        raise ValueError(
            "La pregunta de banco "
            f"{fila['banco_pregunta_id']} tiene una "
            "respuesta correcta no válida: "
            f"{respuesta_correcta}"
        )

    return {
        "id": fila["banco_pregunta_id"],
        "banco_pregunta_id": fila[
            "banco_pregunta_id"
        ],
        "pregunta_importada_id": fila[
            "pregunta_importada_id"
        ],

        "convocatoria_id": fila[
            "convocatoria_id"
        ],
        "codigo_cfg": fila["codigo_cfg"],

        "examen_id": fila["examen_id"],
        "numero_original": fila["numero"],
        "numero_simulacro": None,

        "tipo_examen": fila["tipo_examen"],
        "nombre_archivo": fila["nombre_archivo"],
        "origen": "BANCO",

        "tipo_pregunta": fila["tipo_pregunta"],
        "parte": fila["parte_nombre"],
        "tema": fila["tema_numero"],
        "tema_id": fila["tema_id"],

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
    codigo_cfg=CODIGO_CFG_DEFAULT,
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

        convocatoria_id = obtener_convocatoria_id(
            conn=conn,
            codigo_cfg=codigo_cfg,
        )

        sql = """
            SELECT
                bp.id AS banco_pregunta_id,
                bp.pregunta_importada_id,
                bp.convocatoria_id,
                bp.tema_id,
                bp.fragmento_id,
                bp.enunciado,
                bp.respuesta_correcta,

                c.codigo_cfg,

                pt.nombre AS parte_nombre,

                t.numero AS tema_numero,

                pi.examen_id,
                pi.numero,
                epc.tipo_pregunta,
                pi.norma_detectada,
                pi.articulo_detectado,

                e.tipo_examen,
                e.nombre_archivo

            FROM banco_preguntas bp

            JOIN evaluaciones_preguntas_convocatoria epc
                ON epc.pregunta_importada_id = bp.pregunta_importada_id
            AND epc.convocatoria_id = bp.convocatoria_id

            JOIN convocatorias c
                ON c.id = bp.convocatoria_id

            JOIN partes_temario pt
                ON pt.id = bp.parte_id

            JOIN temas t
                ON t.id = bp.tema_id

            LEFT JOIN preguntas_importadas pi
                ON pi.id = bp.pregunta_importada_id

            LEFT JOIN examenes e
                ON e.id = pi.examen_id

            WHERE
                bp.convocatoria_id = ?

                AND bp.estado = 'VALIDADA'

                AND epc.tipo_pregunta = ?
                
                AND t.numero = ?
        """

        parametros = [
            convocatoria_id,
            tipo_pregunta,
            tema,
        ]

        if excluidas:

            marcadores = ",".join(
                "?"
                for _ in excluidas
            )

            sql += f"""
                AND bp.id NOT IN (
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
        codigo_cfg=CODIGO_CFG_DEFAULT,
        tipo_pregunta="GENERAL",
        tema=1,
        cantidad=5,
    )

    print()
    print("=" * 80)
    print("PRUEBA SELECTOR BANCO")
    print("=" * 80)

    print(
        f"Convocatoria...: {CODIGO_CFG_DEFAULT}"
    )

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
            f"Banco ID.......: "
            f"{pregunta['banco_pregunta_id']}"
        )
        print(
            f"Importada ID...: "
            f"{pregunta['pregunta_importada_id']}"
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
            f"Parte..........: {pregunta['parte']}"
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