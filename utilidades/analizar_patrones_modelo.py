"""
Archivo: analizar_patrones_modelo.py
Ruta: utilidades/analizar_patrones_modelo.py

Analiza las diferencias formales entre las preguntas
ESPECIAL_TEORIA y ESPECIAL_PRACTICA del examen MODELO.

No modifica la base de datos.
"""

import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"


INICIOS = (
    "según",
    "señale",
    "indique",
    "de acuerdo con",
    "conforme a",
    "cuál",
    "qué",
    "cómo",
    "quién",
    "en relación con",
)


PATRONES_PERSONA = (
    r"\bjuan\b",
    r"\bmaría\b",
    r"\bfructuosa\b",
    r"\bmariano\b",
    r"\bun funcionario\b",
    r"\buna funcionaria\b",
    r"\bun interesado\b",
    r"\buna interesada\b",
    r"\bun particular\b",
    r"\buna ciudadana\b",
    r"\bun ciudadano\b",
)


PATRONES_ORGANO_ACTUANDO = (
    r"\bla conselleria\b",
    r"\buna conselleria\b",
    r"\bla dirección general\b",
    r"\bel director general\b",
    r"\bel ayuntamiento\b",
    r"\bun ayuntamiento\b",
    r"\bel órgano de contratación\b",
    r"\bla intervención delegada\b",
)


PATRONES_ACCION = (
    r"\bpretende\b",
    r"\bpresenta\b",
    r"\bsolicita\b",
    r"\binterpone\b",
    r"\bdicta\b",
    r"\btramita\b",
    r"\bincoa\b",
    r"\bconvoca\b",
    r"\bha sido\b",
    r"\bva a\b",
    r"\bse plantea\b",
)


PATRON_FECHA = re.compile(
    r"\b\d{1,2}\s+de\s+"
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|"
    r"agosto|septiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+\d{4})?\b",
    re.IGNORECASE,
)


PATRON_IMPORTE = re.compile(
    r"\b\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*euros\b",
    re.IGNORECASE,
)


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


def normalizar(texto):

    texto = str(texto or "").strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return " ".join(
        texto.replace("\n", " ").split()
    )


def cargar_preguntas(conn):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pi.id,
            pi.numero,
            pi.tipo_pregunta,
            pi.enunciado
        FROM preguntas_importadas pi
        JOIN examenes e
            ON e.id = pi.examen_id
        WHERE
            e.tipo_examen = 'MODELO'
            AND pi.tipo_pregunta IN (
                'ESPECIAL_TEORIA',
                'ESPECIAL_PRACTICA'
            )
        ORDER BY
            pi.tipo_pregunta,
            pi.numero
        """
    )

    return cur.fetchall()


def empieza_por(texto, inicio):

    return texto.startswith(
        normalizar(inicio)
    )


def contiene_patron(texto, patrones):

    return any(
        re.search(
            patron,
            texto,
            flags=re.IGNORECASE,
        )
        for patron in patrones
    )


def analizar_grupo(preguntas):

    resumen = Counter()

    longitudes = []

    ejemplos = {
        "persona": [],
        "organo": [],
        "fecha": [],
        "importe": [],
        "accion": [],
    }

    for pregunta in preguntas:

        enunciado_original = pregunta["enunciado"]

        texto = normalizar(
            enunciado_original
        )

        longitudes.append(
            len(enunciado_original)
        )

        for inicio in INICIOS:

            if empieza_por(
                texto,
                inicio,
            ):

                resumen[
                    f"INICIO::{inicio}"
                ] += 1

        tiene_persona = contiene_patron(
            texto,
            PATRONES_PERSONA,
        )

        tiene_organo = contiene_patron(
            texto,
            PATRONES_ORGANO_ACTUANDO,
        )

        tiene_accion = contiene_patron(
            texto,
            PATRONES_ACCION,
        )

        tiene_fecha = bool(
            PATRON_FECHA.search(
                enunciado_original
            )
        )

        tiene_importe = bool(
            PATRON_IMPORTE.search(
                enunciado_original
            )
        )

        if tiene_persona:

            resumen["PERSONA"] += 1

            ejemplos["persona"].append(
                pregunta["numero"]
            )

        if tiene_organo:

            resumen["ORGANO"] += 1

            ejemplos["organo"].append(
                pregunta["numero"]
            )

        if tiene_accion:

            resumen["ACCION"] += 1

            ejemplos["accion"].append(
                pregunta["numero"]
            )

        if tiene_fecha:

            resumen["FECHA"] += 1

            ejemplos["fecha"].append(
                pregunta["numero"]
            )

        if tiene_importe:

            resumen["IMPORTE"] += 1

            ejemplos["importe"].append(
                pregunta["numero"]
            )

        if (
            tiene_accion
            and (
                tiene_persona
                or tiene_organo
            )
        ):

            resumen["SUJETO_MAS_ACCION"] += 1

        if (
            tiene_accion
            and (
                tiene_fecha
                or tiene_importe
            )
        ):

            resumen["ACCION_MAS_DATO"] += 1

    total = len(
        preguntas
    )

    media = (
        sum(longitudes) / total
        if total
        else 0
    )

    return {
        "total": total,
        "resumen": resumen,
        "longitud_media": media,
        "longitud_minima": min(
            longitudes,
            default=0,
        ),
        "longitud_maxima": max(
            longitudes,
            default=0,
        ),
        "ejemplos": ejemplos,
    }


def porcentaje(cantidad, total):

    if total == 0:
        return 0.0

    return cantidad * 100 / total


def mostrar_grupo(nombre, analisis):

    total = analisis["total"]

    resumen = analisis["resumen"]

    print()
    print("=" * 80)
    print(nombre)
    print("=" * 80)

    print(
        f"Preguntas................: {total}"
    )

    print(
        f"Longitud media...........: "
        f"{analisis['longitud_media']:.2f}"
    )

    print(
        f"Longitud mínima..........: "
        f"{analisis['longitud_minima']}"
    )

    print(
        f"Longitud máxima..........: "
        f"{analisis['longitud_maxima']}"
    )

    print()
    print("INICIOS")

    for inicio in INICIOS:

        cantidad = resumen[
            f"INICIO::{inicio}"
        ]

        print(
            f"{inicio:<24}: "
            f"{cantidad:>2} "
            f"({porcentaje(cantidad, total):6.2f} %)"
        )

    print()
    print("RASGOS")

    for clave, etiqueta in (
        ("PERSONA", "Persona concreta"),
        ("ORGANO", "Órgano concreto"),
        ("ACCION", "Acción narrativa"),
        ("FECHA", "Fecha concreta"),
        ("IMPORTE", "Importe concreto"),
        (
            "SUJETO_MAS_ACCION",
            "Sujeto + acción",
        ),
        (
            "ACCION_MAS_DATO",
            "Acción + fecha/importe",
        ),
    ):

        cantidad = resumen[
            clave
        ]

        print(
            f"{etiqueta:<24}: "
            f"{cantidad:>2} "
            f"({porcentaje(cantidad, total):6.2f} %)"
        )


def mostrar_diferencias(
    teoria,
    practica,
):

    print()
    print("=" * 80)
    print("DIFERENCIAS")
    print("=" * 80)

    rasgos = (
        ("PERSONA", "Persona concreta"),
        ("ORGANO", "Órgano concreto"),
        ("ACCION", "Acción narrativa"),
        ("FECHA", "Fecha concreta"),
        ("IMPORTE", "Importe concreto"),
        (
            "SUJETO_MAS_ACCION",
            "Sujeto + acción",
        ),
        (
            "ACCION_MAS_DATO",
            "Acción + fecha/importe",
        ),
    )

    for clave, etiqueta in rasgos:

        pct_teoria = porcentaje(
            teoria["resumen"][clave],
            teoria["total"],
        )

        pct_practica = porcentaje(
            practica["resumen"][clave],
            practica["total"],
        )

        diferencia = (
            pct_practica
            - pct_teoria
        )

        print(
            f"{etiqueta:<24}: "
            f"Teoría {pct_teoria:6.2f} % | "
            f"Práctica {pct_practica:6.2f} % | "
            f"Diferencia {diferencia:+7.2f}"
        )


def main():

    conn = abrir_conexion()

    try:

        preguntas = cargar_preguntas(
            conn
        )

    finally:

        conn.close()

    teoria = [
        pregunta
        for pregunta in preguntas
        if pregunta["tipo_pregunta"]
        == "ESPECIAL_TEORIA"
    ]

    practica = [
        pregunta
        for pregunta in preguntas
        if pregunta["tipo_pregunta"]
        == "ESPECIAL_PRACTICA"
    ]

    analisis_teoria = analizar_grupo(
        teoria
    )

    analisis_practica = analizar_grupo(
        practica
    )

    mostrar_grupo(
        "ESPECIAL_TEORIA",
        analisis_teoria,
    )

    mostrar_grupo(
        "ESPECIAL_PRACTICA",
        analisis_practica,
    )

    mostrar_diferencias(
        teoria=analisis_teoria,
        practica=analisis_practica,
    )


if __name__ == "__main__":

    main()
    