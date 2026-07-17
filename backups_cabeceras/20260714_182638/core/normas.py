"""
Archivo: normas.py
Ruta: core/normas.py

Carga y normaliza el catálogo de normas.

Permite:
- obtener alias de cada norma;
- convertir códigos internos en prefijos de documentos;
- detectar normas citadas en textos;
- recuperar una norma por su código.

No modifica la base de datos.
"""

import csv
import re
import unicodedata
from pathlib import Path


CSV_NORMAS = Path(
    "config/normas.csv"
)


def normalizar(
    texto,
):

    texto = texto or ""

    texto = unicodedata.normalize(
        "NFD",
        texto.lower(),
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(
            caracter
        ) != "Mn"
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def alias_especiales(
    codigo,
):

    especiales = {

        "CE": [
            "constitucion española",
            "constitucion",
            "ce",
        ],

        "RLC": [
            "reglamento de les corts",
            "reglamento de las corts",
            "reglamento de les corts valencianes",
        ],

        "TFUE": [
            (
                "tratado de funcionamiento "
                "de la union europea"
            ),
            (
                "tratado funcionamiento "
                "union europea"
            ),
            "tfue",
        ],

        "TUE": [
            "tratado de la union europea",
            "tratado union europea",
            "tue",
        ],

        "LO5_1982": [
            "ley organica 5/1982",
            "estatuto de autonomia",
            (
                "estatuto de autonomia "
                "de la comunitat valenciana"
            ),
            (
                "estatuto de autonomia "
                "de la comunidad valenciana"
            ),
            "eacv",
        ],

        "DL5_2015": [
            (
                "real decreto legislativo "
                "5/2015"
            ),
            (
                "decreto legislativo "
                "5/2015"
            ),
            "trebep",
            (
                "texto refundido del estatuto "
                "basico del empleado publico"
            ),
            (
                "estatuto basico del "
                "empleado publico"
            ),
        ],

        "LO3_2018": [
            "ley organica 3/2018",
            (
                "ley organica de proteccion "
                "de datos personales"
            ),
            (
                "proteccion de datos "
                "personales"
            ),
            (
                "garantia de los derechos "
                "digitales"
            ),
            "lopdgdd",
        ],
    }

    return especiales.get(
        codigo,
        [],
    )


def alias_desde_codigo(
    codigo,
):

    alias = list(
        alias_especiales(
            codigo
        )
    )

    if codigo in {
        "CE",
        "RLC",
        "TFUE",
        "TUE",
        "LO5_1982",
        "DL5_2015",
        "LO3_2018",
    }:

        return alias

    coincidencia = re.fullmatch(
        r"(DL|LO|D|L)(\d+)_(\d{4})",
        codigo,
    )

    if coincidencia is None:

        return alias

    tipo, numero, anio = (
        coincidencia.groups()
    )

    referencia = (
        f"{numero}/{anio}"
    )

    if tipo == "LO":

        alias.append(
            f"ley organica {referencia}"
        )

    elif tipo == "DL":

        alias.extend(
            [
                (
                    "decreto legislativo "
                    f"{referencia}"
                ),
                (
                    "real decreto legislativo "
                    f"{referencia}"
                ),
            ]
        )

    elif tipo == "D":

        alias.append(
            f"decreto {referencia}"
        )

    else:

        alias.append(
            f"ley {referencia}"
        )

    return alias


def codigo_a_prefijo(
    codigo,
):

    especiales = {
        "CE": (
            "Constitucion Española"
        ),
        "RLC": (
            "Reglamento de Les Corts"
        ),
        "TFUE": (
            "Tratado Funcionamiento "
            "Union Europea"
        ),
        "TUE": (
            "Tratado Union Europea"
        ),
    }

    if codigo in especiales:

        return especiales[
            codigo
        ]

    if codigo.startswith(
        "DL"
    ):

        return (
            "Decreto Legislativo "
            + codigo[2:]
        )

    if codigo.startswith(
        "LO"
    ):

        return (
            "Ley Orgánica "
            + codigo[2:]
        )

    if codigo.startswith(
        "D"
    ):

        return (
            "Decreto "
            + codigo[1:]
        )

    if codigo.startswith(
        "L"
    ):

        return (
            "Ley "
            + codigo[1:]
        )

    raise ValueError(
        f"Código desconocido: {codigo}"
    )


def cargar_normas():

    if not CSV_NORMAS.exists():

        raise FileNotFoundError(
            "No existe el catálogo de normas: "
            f"{CSV_NORMAS.resolve()}"
        )

    normas = []

    with CSV_NORMAS.open(
        encoding="utf-8-sig",
        newline="",
    ) as fichero:

        lector = csv.DictReader(
            fichero,
            delimiter=";",
        )

        for fila in lector:

            codigo = str(
                fila.get(
                    "codigo",
                    "",
                )
            ).strip()

            if not codigo:

                continue

            alias = alias_desde_codigo(
                codigo
            )

            for campo in (
                "titulo_corto",
                "titulo_oficial",
            ):

                valor = normalizar(
                    fila.get(
                        campo,
                        "",
                    )
                )

                if valor:

                    alias.append(
                        valor
                    )

            alias_normalizados = {
                normalizar(
                    valor
                )
                for valor in alias
                if normalizar(
                    valor
                )
            }

            normas.append(
                {
                    "codigo": codigo,

                    "prefijo": (
                        codigo_a_prefijo(
                            codigo
                        )
                    ),

                    "titulo_oficial": str(
                        fila.get(
                            "titulo_oficial",
                            "",
                        )
                    ).strip(),

                    "titulo_corto": str(
                        fila.get(
                            "titulo_corto",
                            "",
                        )
                    ).strip(),

                    "alias": sorted(
                        alias_normalizados,
                        key=len,
                        reverse=True,
                    ),
                }
            )

    return normas


def detectar_normas(
    texto,
    normas,
):

    texto_normalizado = normalizar(
        texto
    )

    if not texto_normalizado:

        return []

    detectadas = []

    for norma in normas:

        coincide = any(
            alias
            and alias
            in texto_normalizado
            for alias in norma[
                "alias"
            ]
        )

        if coincide:

            detectadas.append(
                norma
            )

    return detectadas


def obtener_norma(
    codigo,
    normas,
):

    for norma in normas:

        if norma[
            "codigo"
        ] == codigo:

            return norma

    return None