"""
Archivo: clasificar_modelo.py
Ruta: procesos/clasificar_modelo.py

Clasifica temáticamente las preguntas del examen MODELO.

Para cada pregunta:
- obtiene norma, artículo, documento, fragmento, parte temática y tema
  mediante core.clasificador.Clasificador;
- asigna tipo_pregunta según la posición oficial en el examen;
- no modifica preguntas de exámenes de APOYO;
- por defecto funciona en modo PRUEBA;
- solo guarda con --guardar.
"""

import argparse
import sqlite3
from collections import Counter
from pathlib import Path
import sys

from core.clasificador import Clasificador
from core.temario import Temario


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"
RUTA_CFG = ROOT / "config" / "C1-01_58_26.cfg"


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Clasifica temáticamente las preguntas "
            "del examen MODELO."
        )
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help=(
            "Número máximo de preguntas a procesar. "
            "Sin límite por defecto."
        ),
    )

    parser.add_argument(
        "--desde",
        type=int,
        default=None,
        help="Número inicial de pregunta MODELO.",
    )

    parser.add_argument(
        "--hasta",
        type=int,
        default=None,
        help="Número final de pregunta MODELO.",
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help="Guarda los resultados en la base de datos.",
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
            f"{RUTA_BD}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    return conn


def obtener_tipo_pregunta(numero):

    numero = int(numero)

    if 1 <= numero <= 50:
        return "ESPECIAL_TEORIA"

    if 51 <= numero <= 65:
        return "ESPECIAL_PRACTICA"

    if 66 <= numero <= 80:
        return "ESPECIAL_INFORMATICA"

    if 81 <= numero <= 110:
        return "GENERAL"

    raise ValueError(
        "Número de pregunta MODELO fuera "
        f"del rango 1-110: {numero}"
    )


def obtener_parte_origen(tipo_pregunta):

    if tipo_pregunta == "ESPECIAL_INFORMATICA":
        return "Especial-Informática"

    if tipo_pregunta == "GENERAL":
        return "General"

    return "Especial-Teoría"


CORRECCIONES_MODELO = {
    23: {
        "parte": "Especial-Teoría",
        "tema": 6,
        "norma": "L9_2017",
        "articulo": "40",
        "fragmento_id": 18275,
        "motivo": (
            "Corrección manual del examen MODELO: la respuesta se "
            "justifica por el artículo 40 de la Ley 9/2017."
        ),
    },
    25: {
        "parte": "Especial-Teoría",
        "tema": 7,
        "norma": "D30_2025",
        "articulo": "18",
        "fragmento_id": 16314,
        "motivo": (
            "Corrección manual del examen MODELO: el Decreto 30/2025 "
            "forma parte completa del tema 7 y la referencia es el artículo 18."
        ),
    },
    38: {
        "parte": "Especial-Teoría",
        "tema": 9,
        "norma": "D42_2019",
        "articulo": "21",
        "fragmento_id": 16448,
        "motivo": (
            "Corrección manual del examen MODELO: el Decreto 42/2019 "
            "forma parte completa del tema 9 y la referencia es el artículo 21."
        ),
    },
    41: {
        "parte": "Especial-Teoría",
        "tema": 11,
        "norma": "L1_2015",
        "articulo": "34",
        "fragmento_id": 16831,
        "motivo": (
            "Corrección manual del examen MODELO: la documentación que "
            "acompaña al Proyecto de Ley de Presupuestos se regula en el "
            "artículo 34 de la Ley 1/2015."
        ),
    },
    46: {
        "parte": "Especial-Teoría",
        "tema": 13,
        "norma": "L1_2015",
        "articulo": "100",
        "fragmento_id": None,
        "motivo": (
            "Corrección manual del examen MODELO: las modalidades y el "
            "ejercicio de la función interventora se regulan en el artículo "
            "100 de la Ley 1/2015. El documento correspondiente está pendiente "
            "de incorporarse al corpus documental."
        ),
    },
    61: {
        "parte": "Especial-Teoría",
        "tema": 10,
        "norma": "L4_2021",
        "articulo": "175",
        "fragmento_id": 17694,
        "motivo": (
            "Corrección manual del examen MODELO: la prescripción de las "
            "infracciones disciplinarias se regula en el artículo 175 de "
            "la Ley 4/2021."
        ),
    },
    65: {
        "parte": "Especial-Teoría",
        "tema": 12,
        "norma": "L1_2015",
        "articulo": "50",
        "fragmento_id": 19056,
        "motivo": (
            "Corrección manual del examen MODELO: la generación de crédito "
            "se regula en el artículo 50 de la Ley 1/2015."
        ),
    },
    68: {
        "parte": "Especial-Informática",
        "tema": 21,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Corrección manual del examen MODELO: Archivos bajo demanda "
            "de OneDrive pertenece al tema 21, plataforma colaborativa "
            "Microsoft 365."
        ),
    },
    76: {
        "parte": "Especial-Informática",
        "tema": 23,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Corrección manual del examen MODELO: la comparación entre "
            "personas y modelos de lenguaje pertenece al tema 23, "
            "Herramientas de Inteligencia Artificial."
        ),
    },
    77: {
        "parte": "Especial-Informática",
        "tema": 23,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Corrección manual del examen MODELO: el phishing impulsado "
            "por IA pertenece al tema 23, Herramientas de Inteligencia Artificial."
        ),
    },
    79: {
        "parte": "Especial-Informática",
        "tema": 18,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Corrección manual del examen MODELO: las categorías de Outlook "
            "pertenecen al tema 18, correo electrónico Outlook."
        ),
    },
    64: {
        "parte": "Especial-Teoría",
        "tema": 12,
        "norma": "D25_2017",
        "articulo": "2",
        "fragmento_id": 16274,
        "motivo": (
            "Revisión manual del examen MODELO: clasificación confirmada "
            "en el tema 12."
        ),
    },
    72: {
        "parte": "Especial-Informática",
        "tema": 19,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Revisión manual del examen MODELO: ajuste de texto de imágenes "
            "en Word, tema 19."
        ),
    },
    74: {
        "parte": "Especial-Informática",
        "tema": 21,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Revisión manual del examen MODELO: almacenamiento asociado a "
            "Teams, OneDrive y SharePoint, tema 21."
        ),
    },
    101: {
        "parte": "General",
        "tema": 8,
        "norma": "L5_1983",
        "articulo": "63",
        "fragmento_id": 17928,
        "motivo": (
            "Revisión manual del examen MODELO: clasificación confirmada "
            "en el tema general 8."
        ),
    },
    102: {
        "parte": "General",
        "tema": 8,
        "norma": "L5_1983",
        "articulo": "63",
        "fragmento_id": 17928,
        "motivo": (
            "Revisión manual del examen MODELO: clasificación confirmada "
            "en el tema general 8."
        ),
    },
    39: {
    "parte": "Especial-Teoría",
    "tema": 11,
    "norma": "L1_2015",
    "articulo": "25",
    "fragmento_id": 16817,
    "motivo": (
        "Revisión manual del examen MODELO: la definición "
        "y contenido general de los Presupuestos de la Generalitat "
        "pertenece al tema especial 11."
    ),
    },

    51: {
        "parte": "Especial-Teoría",
        "tema": 6,
        "norma": "L9_2017",
        "articulo": "124",
        "fragmento_id": 18526,
        "motivo": (
            "Revisión manual del examen MODELO: las características "
            "técnicas del suministro deben incluirse en el pliego de "
            "prescripciones técnicas. Tema especial 6."
        ),
    },

    70: {
        "parte": "Especial-Informática",
        "tema": 18,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Revisión manual del examen MODELO: creación de reglas "
            "automáticas y movimiento de mensajes en Outlook, tema 18."
        ),
    },

    78: {
        "parte": "Especial-Informática",
        "tema": 16,
        "norma": None,
        "articulo": None,
        "fragmento_id": None,
        "motivo": (
            "Revisión manual del examen MODELO: organización de "
            "aplicaciones en el menú Inicio de Windows 11, tema 16."
        ),
    },
    
}


def aplicar_correccion_modelo(
    numero,
    resultado,
):

    correccion = CORRECCIONES_MODELO.get(
        int(numero)
    )

    if correccion is None:
        return resultado

    resultado = dict(
        resultado
    )

    resultado.update({
        "resuelta": True,
        "estado": "VALIDADA",
        "parte": correccion["parte"],
        "tema": correccion["tema"],
        "norma": correccion["norma"],
        "articulo": correccion["articulo"],
        "fragmento_id": correccion["fragmento_id"],
        "confianza": 1.0,
        "metodo_validacion": "MODELO_REVISION_MANUAL",
        "motivo": correccion["motivo"],
    })

    return resultado


def cargar_preguntas_modelo(
    conn,
    limite,
    desde,
    hasta,
):

    condiciones = [
        "e.tipo_examen = 'MODELO'",
        """
        (
            pi.metodo_validacion IS NULL
            OR TRIM(pi.metodo_validacion) = ''
        )
        """,
        "pi.tema_detectado IS NULL",
    ]

    parametros = []

    if desde is not None:

        condiciones.append(
            "pi.numero >= ?"
        )

        parametros.append(
            desde
        )

    if hasta is not None:

        condiciones.append(
            "pi.numero <= ?"
        )

        parametros.append(
            hasta
        )

    sql = f"""
        SELECT
            pi.id,
            pi.examen_id,
            pi.numero,
            pi.enunciado,
            pi.respuesta_correcta,
            pi.parte_detectada,
            pi.tema_detectado,
            pi.tipo_pregunta,
            pi.estado_validacion,
            pi.metodo_validacion,
            e.nombre_archivo
        FROM preguntas_importadas pi
        JOIN examenes e
          ON e.id = pi.examen_id
        WHERE
            {' AND '.join(condiciones)}
        ORDER BY
            e.id,
            pi.numero
    """

    if limite is not None:

        sql += """
        LIMIT ?
        """

        parametros.append(
            limite
        )

    cur = conn.cursor()

    cur.execute(
        sql,
        tuple(parametros),
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
    tipo_pregunta,
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
            metodo_validacion = ?,
            tipo_pregunta = ?
        WHERE
            id = ?
            AND tema_detectado IS NULL
            AND (
                metodo_validacion IS NULL
                OR TRIM(metodo_validacion) = ''
            )
            AND examen_id IN (
                SELECT id
                FROM examenes
                WHERE tipo_examen = 'MODELO'
            )
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
            tipo_pregunta,
            pregunta_id,
        ),
    )

    if cur.rowcount != 1:

        raise RuntimeError(
            "No se pudo actualizar la pregunta MODELO "
            f"{pregunta_id}."
        )


def mostrar_resultado(
    pregunta,
    tipo_pregunta,
    resultado,
):

    print()
    print("=" * 80)
    print(
        f"Pregunta ID {pregunta['id']} "
        f"| Número {pregunta['numero']} "
        f"| {pregunta['nombre_archivo']}"
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
        f"Bloque examen.....: "
        f"{tipo_pregunta}"
    )
    print(
        f"Parte temática....: "
        f"{resultado['parte']}"
    )
    print(
        f"Tema..............: "
        f"{resultado['tema']}"
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

    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )

    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )

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
    resultados_bloque = Counter()

    procesadas = 0

    try:

        preguntas = cargar_preguntas_modelo(
            conn=conn,
            limite=argumentos.limite,
            desde=argumentos.desde,
            hasta=argumentos.hasta,
        )

        if not preguntas:

            print(
                "No existen preguntas MODELO "
                "pendientes de clasificación temática."
            )
            return

        temario = Temario(
            RUTA_CFG
        )

        clasificador = Clasificador(
            temario
        )

        print()
        print("=" * 80)
        print("CLASIFICACIÓN TEMÁTICA DEL EXAMEN MODELO")
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

            tipo_pregunta = obtener_tipo_pregunta(
                pregunta["numero"]
            )

            parte_origen = obtener_parte_origen(
                tipo_pregunta
            )

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
                parte_origen=parte_origen,
            )

            resultado = aplicar_correccion_modelo(
                numero=pregunta["numero"],
                resultado=resultado,
            )

            mostrar_resultado(
                pregunta=pregunta,
                tipo_pregunta=tipo_pregunta,
                resultado=resultado,
            )

            resultados_estado[
                resultado["estado"]
            ] += 1

            resultados_metodo[
                resultado["metodo_validacion"]
            ] += 1

            resultados_bloque[
                tipo_pregunta
            ] += 1

            procesadas += 1

            if argumentos.guardar:

                guardar_resultado(
                    conn=conn,
                    pregunta_id=pregunta["id"],
                    tipo_pregunta=tipo_pregunta,
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

    print()
    print("Estados:")

    for estado in (
        "VALIDADA",
        "A_REVISAR",
        "RECHAZADA",
    ):

        print(
            f"- {estado:<12}: "
            f"{resultados_estado[estado]}"
        )

    print()
    print("Bloques del examen:")

    for bloque in (
        "ESPECIAL_TEORIA",
        "ESPECIAL_PRACTICA",
        "ESPECIAL_INFORMATICA",
        "GENERAL",
    ):

        print(
            f"- {bloque:<24}: "
            f"{resultados_bloque[bloque]}"
        )

    print()
    print("Métodos:")

    for metodo, cantidad in sorted(
        resultados_metodo.items(),
        key=lambda item: str(item[0]),
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