"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : buscar_fragmentos.py
Ruta    : core/buscar_fragmentos.py

Objetivo:
    Buscar fragmentos normativos relevantes para una pregunta.

Entradas:
    - Texto de búsqueda.
    - Tema o norma opcionales.

Salidas:
    - Fragmentos ordenados por relevancia.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.temario

Utilizado por:
    - core/clasificador.py

Flujo:
    1. Limita los documentos aplicables.
    2. Normaliza y tokeniza el texto.
    3. Calcula relevancia.
    4. Devuelve los mejores fragmentos.

Observaciones:
    - Ninguna.

==============================================================================
"""
import math
import re
import sqlite3
import unicodedata
from collections import Counter

from core.temario import Temario


STOPWORDS = {
    "a", "al", "ante", "bajo", "con", "contra", "de", "del",
    "desde", "durante", "e", "el", "ella", "en", "entre",
    "es", "esta", "este", "la", "las", "lo", "los", "o",
    "para", "por", "que", "se", "segun", "sin", "sobre",
    "su", "sus", "un", "una", "y",
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


def obtener_documentos_busqueda(
    temario,
    codigo_norma=None,
):

    if not isinstance(temario, Temario):
        raise TypeError(
            "temario debe ser una instancia de Temario."
        )

    if codigo_norma is None:
        return temario.obtener_documentos()

    if not temario.norma_pertenece(
        codigo_norma
    ):
        return ()

    return temario.obtener_documentos_norma(
        codigo_norma
    )


def cargar_fragmentos(
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
            f.id,
            f.documento_id,
            f.referencia,
            f.articulo,
            f.texto,
            d.nombre_archivo
        FROM fragmentos f
        JOIN documentos d
            ON d.id = f.documento_id
        WHERE d.nombre_archivo IN ({marcadores})
        ORDER BY f.id
        """,
        tuple(documentos),
    )

    return cur.fetchall()


def buscar_fragmentos(
    conn,
    temario,
    texto_consulta,
    codigo_norma=None,
    limite=5,
):

    if limite < 1:
        raise ValueError(
            "limite debe ser mayor que cero."
        )

    documentos_permitidos = (
        obtener_documentos_busqueda(
            temario=temario,
            codigo_norma=codigo_norma,
        )
    )

    filas = cargar_fragmentos(
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

        tokens = tokenizar(
            fila["texto"]
        )

        frecuencias = Counter(tokens)

        documentos_bm25.append({
            "fila": fila,
            "tokens": tokens,
            "frecuencias": frecuencias,
        })

        for token in frecuencias:
            frecuencia_documentos[token] += 1

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

        fila = documento["fila"]

        resultados.append({
            "fragmento_id": fila["id"],
            "documento_id": fila[
                "documento_id"
            ],
            "referencia": fila[
                "referencia"
            ],
            "articulo": fila[
                "articulo"
            ],
            "texto": fila["texto"],
            "nombre_archivo": fila[
                "nombre_archivo"
            ],
            "score": score,
        })

    resultados.sort(
        key=lambda resultado: resultado[
            "score"
        ],
        reverse=True,
    )

    return resultados[:limite]