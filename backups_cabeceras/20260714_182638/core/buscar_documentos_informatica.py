"""
Archivo: buscar_documentos_informatica.py
Ruta: core/buscar_documentos_informatica.py

Dependencias:
- math
- re
- sqlite3
- unicodedata
- collections
- core.temario

Funcionalidad:
Localiza documentos candidatos de Informática mediante BM25.

La búsqueda se realiza exclusivamente sobre el campo texto_extraido de los
documentos asociados a temas de Informática definidos en el Temario.

Este módulo no trabaja con artículos ni fragmentos jurídicos.

BM25 únicamente devuelve documentos candidatos. No valida preguntas ni
asigna directamente temas.

No modifica la base de datos.
"""

import math
import re
import sqlite3
import unicodedata
from collections import Counter

from core.temario import Temario


STOPWORDS = {
    "a",
    "al",
    "ante",
    "bajo",
    "con",
    "contra",
    "de",
    "del",
    "desde",
    "durante",
    "e",
    "el",
    "ella",
    "en",
    "entre",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "o",
    "para",
    "por",
    "que",
    "se",
    "segun",
    "sin",
    "sobre",
    "su",
    "sus",
    "un",
    "una",
    "y",
}


def normalizar(texto):

    texto = unicodedata.normalize(
        "NFD",
        (texto or "").lower(),
    )

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def tokenizar(texto):

    tokens = re.findall(
        r"[a-z0-9]{2,}",
        normalizar(texto),
    )

    return [
        token
        for token in tokens
        if token not in STOPWORDS
    ]


def obtener_documentos_informatica(
    temario,
):

    if not isinstance(
        temario,
        Temario,
    ):

        raise TypeError(
            "temario debe ser una instancia de Temario."
        )

    documentos = set()

    for tema in temario.obtener_temas():

        if not temario.es_informatica(
            tema["parte"],
            tema["numero"],
        ):
            continue

        documentos.update(
            tema["documentos"]
        )

    return tuple(
        sorted(documentos)
    )


def cargar_documentos(
    conn,
    documentos,
):

    if not documentos:
        return []

    marcadores = ",".join(
        "?"
        for _ in documentos
    )

    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT
            id,
            nombre_archivo,
            titulo,
            texto_extraido
        FROM documentos
        WHERE nombre_archivo IN ({marcadores})
        ORDER BY id
        """,
        tuple(documentos),
    )

    return cur.fetchall()


def buscar_documentos_informatica(
    conn,
    temario,
    texto_consulta,
    limite=5,
):

    if conn is None:
        raise ValueError(
            "conn no puede ser None."
        )

    if limite < 1:
        raise ValueError(
            "limite debe ser mayor que cero."
        )

    documentos_permitidos = (
        obtener_documentos_informatica(
            temario
        )
    )

    filas = cargar_documentos(
        conn=conn,
        documentos=documentos_permitidos,
    )

    if not filas:
        return []

    tokens_consulta = tokenizar(
        texto_consulta
    )

    if not tokens_consulta:
        return []

    documentos_bm25 = []
    frecuencia_documentos = Counter()

    for fila in filas:

        texto = fila[
            "texto_extraido"
        ] or ""

        tokens = tokenizar(
            texto
        )

        frecuencias = Counter(
            tokens
        )

        documentos_bm25.append({
            "fila": fila,
            "tokens": tokens,
            "frecuencias": frecuencias,
        })

        for token in frecuencias:
            frecuencia_documentos[
                token
            ] += 1

    total_documentos = len(
        documentos_bm25
    )

    longitud_media = (
        sum(
            len(documento["tokens"])
            for documento in documentos_bm25
        )
        / total_documentos
    )

    k1 = 1.5
    b = 0.75

    resultados = []

    for documento in documentos_bm25:

        longitud = len(
            documento["tokens"]
        )

        score = 0.0

        for token in set(
            tokens_consulta
        ):

            frecuencia = documento[
                "frecuencias"
            ].get(
                token,
                0,
            )

            if frecuencia == 0:
                continue

            df = frecuencia_documentos[
                token
            ]

            idf = math.log(
                1
                + (
                    total_documentos
                    - df
                    + 0.5
                )
                / (
                    df
                    + 0.5
                )
            )

            denominador = (
                frecuencia
                + k1
                * (
                    1
                    - b
                    + b
                    * longitud
                    / max(
                        longitud_media,
                        1,
                    )
                )
            )

            score += (
                idf
                * (
                    frecuencia
                    * (
                        k1
                        + 1
                    )
                )
                / denominador
            )

        if score <= 0:
            continue

        fila = documento[
            "fila"
        ]

        asociaciones = (
            temario.obtener_asociaciones_documento(
                fila["nombre_archivo"]
            )
        )

        resultados.append({
            "documento_id": fila["id"],
            "nombre_archivo": fila[
                "nombre_archivo"
            ],
            "titulo": fila["titulo"],
            "texto": fila[
                "texto_extraido"
            ],
            "asociaciones": asociaciones,
            "score": score,
        })

    resultados.sort(
        key=lambda resultado: resultado[
            "score"
        ],
        reverse=True,
    )

    return resultados[
        :limite
    ]


def main():

    from pathlib import Path

    ruta_bd = Path(
        "db/oposiciones.sqlite3"
    )

    if not ruta_bd.exists():

        raise FileNotFoundError(
            "No existe la base de datos: "
            f"{ruta_bd.resolve()}"
        )

    temario = Temario()

    conn = sqlite3.connect(
        ruta_bd
    )

    try:

        consulta = (
            "En Microsoft Excel, ¿qué función "
            "permite sumar los valores de un "
            "rango de celdas? "
            "La función SUMA."
        )

        resultados = (
            buscar_documentos_informatica(
                conn=conn,
                temario=temario,
                texto_consulta=consulta,
                limite=5,
            )
        )

        print()
        print("=" * 80)
        print(
            "BÚSQUEDA DE DOCUMENTOS "
            "DE INFORMÁTICA"
        )
        print("=" * 80)
        print(
            f"Resultados: {len(resultados)}"
        )

        for posicion, resultado in enumerate(
            resultados,
            start=1,
        ):

            print()
            print(
                f"{posicion}. "
                f"{resultado['nombre_archivo']}"
            )
            print(
                f"Score: "
                f"{resultado['score']:.4f}"
            )

            for asociacion in resultado[
                "asociaciones"
            ]:

                print(
                    f"Parte: "
                    f"{asociacion['parte']}"
                )
                print(
                    f"Tema: "
                    f"{asociacion['tema']}"
                )

    finally:

        conn.close()


if __name__ == "__main__":
    main()