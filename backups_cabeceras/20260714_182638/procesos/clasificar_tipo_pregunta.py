"""
Archivo: clasificar_tipo_pregunta.py
Ruta: procesos/clasificar_tipo_pregunta.py

Clasifica el tipo de las preguntas VALIDADA que todavía
no tienen tipo_pregunta asignado.

Reglas:
- Parte General -> GENERAL.
- Parte Especial-Informática -> ESPECIAL_INFORMATICA.
- Parte Especial:
    - sujeto concreto + actuación narrativa -> ESPECIAL_PRACTICA;
    - formulación normativa o abstracta -> ESPECIAL_TEORIA;
    - caso no concluyente -> PENDIENTE_IA.

Por defecto no modifica la base de datos.
Solo guarda clasificaciones definitivas con --guardar.
Las preguntas PENDIENTE_IA permanecen sin modificar.
"""

import argparse
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


TIPOS_DEFINITIVOS = {
    "GENERAL",
    "ESPECIAL_TEORIA",
    "ESPECIAL_PRACTICA",
    "ESPECIAL_INFORMATICA",
}

CORRECCIONES_MANUALES = {
    189: "ESPECIAL_TEORIA",
    717: "ESPECIAL_PRACTICA",
    718: "ESPECIAL_PRACTICA",
    719: "ESPECIAL_PRACTICA",
    721: "ESPECIAL_PRACTICA",
    730: "ESPECIAL_PRACTICA",
}

INICIOS_TEORICOS = (
    "segun ",
    "senale ",
    "indique ",
    "de acuerdo con ",
    "conforme a ",
    "en relacion con ",
    "cual ",
    "que ",
    "como ",
    "quien ",
    "cuando ",
    "donde ",
    "entre ",
    "las ",
    "los ",
)


PATRONES_SUJETO_CONCRETO = (
    r"\bfructuosa\b",
    r"\bmariano\b",

    r"\b(?:el|un) funcionario\b",
    r"\b(?:la|una) funcionaria\b",

    r"\b(?:el|un) interesado\b",
    r"\b(?:la|una) interesada\b",

    r"\b(?:el|un) particular\b",
    r"\b(?:la|una) ciudadana\b",
    r"\b(?:el|un) ciudadano\b",

    r"\b(?:la|una) conselleria\b",
    r"\bconselleria [a-z]\b",

    r"\b(?:la|una) direccion general\b",
    r"\b(?:el|un) director general\b",

    r"\b(?:el|un) ayuntamiento\b",

    r"\b(?:el|un) organo de contratacion\b",
    r"\b(?:la|una) intervencion delegada\b",

    r"\b(?:la|una) empresa\b",
    r"\b(?:el|un) licitador\b",

    r"\bpersona tecnica encargada\b",
    r"\bjefa de seccion\b",

    r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-Z]\.){1,3}\s+(?:es|se encuentra|ha|presenta|solicita|interpone|pretende|ocupa)\b",
    r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+(?:es|se encuentra|ha|presenta|solicita|interpone|pretende|ocupa)\b",
)


PATRONES_ACCION_NARRATIVA = (
    r"\bpretende\b",
    r"\bva a\b",
    r"\bpresenta\b",
    r"\bsolicita\b",
    r"\binterpone\b",
    r"\bdicta\b",
    r"\btramita\b",
    r"\bse esta tramitando\b",
    r"\bincoa\b",
    r"\bconvoca\b",
    r"\badjudica\b",
    r"\bresuelve\b",
    r"\bcomunica\b",
    r"\brecibe\b",
    r"\bse plantea\b",
    r"\bha sido\b",
    r"\besta tramitando\b",
    r"\besta previsto\b",
    r"\bse asigna\b",
    r"\bse presenta\b",
    r"\bdesempenas tus funciones\b",
    r"\beres la persona\b",
)


PATRONES_SUPUESTO_EXPRESO = (
    r"\bsuponga que\b",
    r"\bsupongamos que\b",
    r"\bimagine que\b",
    r"\ben el supuesto de que\b",
    r"\bsupuesto de hecho\b",
    r"\bcaso planteado\b",
)

MESES = (
    "enero", "febrero", "marzo", "abril",
    "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
)

PATRONES_SECUENCIA = (
    r"\bposteriormente\b",
    r"\bdespues\b",
    r"\btras\b",
    r"\bmas tarde\b",
    r"\bde nuevo\b",
    r"\bfinalmente\b",
)

PATRONES_ACTUACION = (
    r"\bsolicita\b",
    r"\bpresenta\b",
    r"\bmodifica\b",
    r"\bresuelve\b",
    r"\bdicta\b",
    r"\bnotifica\b",
    r"\btramita\b",
    r"\bincoa\b",
    r"\badjudica\b",
    r"\bautoriza\b",
    r"\bdeniega\b",
    r"\baprueba\b",
    r"\bacuerda\b",
)


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Clasifica tipo_pregunta en preguntas "
            "VALIDADA pendientes."
        )
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help=(
            "Guarda únicamente las clasificaciones "
            "definitivas."
        ),
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Número máximo de preguntas a procesar.",
    )

    parser.add_argument(
        "--mostrar-practicas",
        action="store_true",
        help=(
            "Muestra las preguntas clasificadas como "
            "ESPECIAL_PRACTICA."
        ),
    )

    parser.add_argument(
        "--mostrar-pendientes",
        action="store_true",
        help=(
            "Muestra las preguntas clasificadas como "
            "PENDIENTE_IA."
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


def normalizar_texto(
    texto,
):

    texto = str(
        texto or ""
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(
            caracter
        ) != "Mn"
    )

    return " ".join(
        texto.replace(
            "\n",
            " ",
        ).split()
    )


def contiene_patron(
    texto,
    patrones,
):

    return any(
        re.search(
            patron,
            texto,
            flags=re.IGNORECASE,
        )
        is not None
        for patron in patrones
    )


def cargar_preguntas(
    conn,
    limite,
):

    sql = """
        SELECT
            pi.id,
            pi.examen_id,
            pi.numero,
            pi.enunciado,
            pi.parte_detectada,
            pi.tema_detectado,
            pi.norma_detectada,
            pi.articulo_detectado,
            e.tipo_examen,
            e.nombre_archivo
        FROM preguntas_importadas pi

        JOIN examenes e
            ON e.id = pi.examen_id

        WHERE
            pi.estado_validacion = 'VALIDADA'

            AND (
                pi.tipo_pregunta IS NULL
                OR TRIM(pi.tipo_pregunta) = ''
            )

        ORDER BY
            e.id,
            pi.numero
    """

    parametros = []

    if limite is not None:

        if limite <= 0:

            raise ValueError(
                "--limite debe ser mayor que cero."
            )

        sql += """
        LIMIT ?
        """

        parametros.append(
            limite
        )

    cur = conn.cursor()

    cur.execute(
        sql,
        parametros,
    )

    return cur.fetchall()


def empieza_como_teorica(
    texto,
):

    texto_sin_signos = texto.lstrip(
        "¿¡"
    )

    return any(
        texto_sin_signos.startswith(
            inicio
        )
        for inicio in INICIOS_TEORICOS
    )

def puntuacion_practica(texto):

    puntos = 0

    # Supuesto expreso
    if contiene_patron(
        texto,
        PATRONES_SUPUESTO_EXPRESO,
    ):
        puntos += 4

    # Persona concreta
    if contiene_patron(
        texto,
        PATRONES_SUJETO_CONCRETO,
    ):
        puntos += 2

    # Organismo en mayúsculas (AVFGA, AEAT...)
    if re.search(
        r"\b[A-Z]{2,}\b",
        texto,
    ):
        puntos += 2

    # Año
    if re.search(
        r"\b20\d{2}\b",
        texto,
    ):
        puntos += 2

    # Mes
    if any(
        mes in texto
        for mes in MESES
    ):
        puntos += 2

    # Porcentaje
    if re.search(
        r"\d+\s*%",
        texto,
    ):
        puntos += 2

    # Cantidades
    if re.search(
        r"\b\d+[.,]?\d*\b",
        texto,
    ):
        puntos += 1

    # Actuaciones
    if contiene_patron(
        texto,
        PATRONES_ACTUACION,
    ):
        puntos += 2

    # Secuencia temporal
    if contiene_patron(
        texto,
        PATRONES_SECUENCIA,
    ):
        puntos += 1

    return puntos

def clasificar_especial(
    enunciado,
):

    texto = normalizar_texto(
        enunciado
    )

    puntos = puntuacion_practica(
        texto
    )

    if puntos >= 5:

        return (
            "ESPECIAL_PRACTICA",
            f"Supuesto práctico detectado ({puntos} puntos).",
        )

    return (
        "ESPECIAL_TEORIA",
        f"Pregunta teórica ({puntos} puntos).",
    )


def clasificar_tipo(
    pregunta,
):
    
    correccion = CORRECCIONES_MANUALES.get(
    pregunta["id"]
    )

    if correccion:

        return (
            correccion,
            "Clasificación manual revisada.",
        )

    parte = normalizar_texto(
        pregunta["parte_detectada"]
    )

    if parte == "general":

        return (
            "GENERAL",
            "La norma y el artículo pertenecen "
            "a la parte General del temario.",
        )

    if parte in {
        "especial-informatica",
        "especial informatica",
    }:

        return (
            "ESPECIAL_INFORMATICA",
            "La pregunta pertenece a la parte "
            "Especial-Informática.",
        )

    if parte in {
        "especial-teoria",
        "especial teoria",
        "especial",
    }:

        return clasificar_especial(
            pregunta["enunciado"]
        )

    raise ValueError(
        "Parte temática no reconocida en la "
        f"pregunta {pregunta['id']}: "
        f"{pregunta['parte_detectada']!r}"
    )


def actualizar_tipo(
    conn,
    pregunta_id,
    tipo_pregunta,
):

    if tipo_pregunta not in TIPOS_DEFINITIVOS:

        raise ValueError(
            "No se puede guardar un tipo no "
            f"definitivo: {tipo_pregunta}"
        )

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE preguntas_importadas
        SET
            tipo_pregunta = ?
        WHERE
            id = ?

            AND estado_validacion = 'VALIDADA'

            AND (
                tipo_pregunta IS NULL
                OR TRIM(tipo_pregunta) = ''
            )
        """,
        (
            tipo_pregunta,
            pregunta_id,
        ),
    )

    if cur.rowcount != 1:

        raise RuntimeError(
            "No se pudo actualizar la pregunta "
            f"{pregunta_id}."
        )


def mostrar_pregunta(
    pregunta,
    tipo_pregunta,
    motivo,
):

    print()
    print("-" * 80)

    print(
        f"ID {pregunta['id']} "
        f"| {pregunta['nombre_archivo']} "
        f"| Nº {pregunta['numero']}"
    )

    print(
        pregunta["enunciado"]
    )

    print(
        f"Clasificación: {tipo_pregunta}"
    )

    print(
        f"Motivo.......: {motivo}"
    )


def main():

    argumentos = crear_argumentos()

    conn = abrir_conexion()

    resumen = Counter()

    guardadas = 0

    try:

        preguntas = cargar_preguntas(
            conn=conn,
            limite=argumentos.limite,
        )

        print()
        print("=" * 80)
        print("CLASIFICACIÓN DE TIPO DE PREGUNTA")
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

            tipo_pregunta, motivo = (
                clasificar_tipo(
                    pregunta
                )
            )

            resumen[
                tipo_pregunta
            ] += 1

            if (
                argumentos.mostrar_practicas
                and tipo_pregunta
                == "ESPECIAL_PRACTICA"
            ):

                mostrar_pregunta(
                    pregunta=pregunta,
                    tipo_pregunta=tipo_pregunta,
                    motivo=motivo,
                )

            if (
                argumentos.mostrar_pendientes
                and tipo_pregunta
                == "PENDIENTE_IA"
            ):

                mostrar_pregunta(
                    pregunta=pregunta,
                    tipo_pregunta=tipo_pregunta,
                    motivo=motivo,
                )

            if (
                argumentos.guardar
                and tipo_pregunta
                in TIPOS_DEFINITIVOS
            ):

                actualizar_tipo(
                    conn=conn,
                    pregunta_id=pregunta["id"],
                    tipo_pregunta=tipo_pregunta,
                )

                guardadas += 1

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

    for tipo in (
        "GENERAL",
        "ESPECIAL_TEORIA",
        "ESPECIAL_PRACTICA",
        "ESPECIAL_INFORMATICA",
        "PENDIENTE_IA",
    ):

        print(
            f"{tipo:<24}: "
            f"{resumen[tipo]}"
        )

    print("-" * 80)

    print(
        f"TOTAL                   : "
        f"{sum(resumen.values())}"
    )

    if argumentos.guardar:

        print(
            f"GUARDADAS               : "
            f"{guardadas}"
        )

        print(
            f"SIN GUARDAR             : "
            f"{resumen['PENDIENTE_IA']}"
        )

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