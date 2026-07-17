"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : extraer_data_informatica.py
Ruta    : procesos/extraer_data_informatica.py

Objetivo:
    Extraer de forma determinista preguntas y opciones desde los PDF
    almacenados en data_informatica.

Entradas:
    - PDF de data_informatica.

Salidas:
    - JSON *_extraido.json en importaciones/informatica.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - PyMuPDF
    - json
    - re
    - pathlib

Utilizado por:
    - Futuro proceso procesar_data_informatica.py.

Flujo:
    1. Lee el texto del PDF.
    2. Detecta preguntas numeradas.
    3. Extrae las opciones A, B, C y D.
    4. Registra incidencias.
    5. Guarda un JSON intermedio.

Observaciones:
    - No utiliza IA.
    - No escribe en la base de datos.

==============================================================================
"""

import argparse
import json
import re
from pathlib import Path
import sqlite3

import fitz


ROOT = Path(__file__).resolve().parents[1]

RUTA_DATOS = ROOT / "data_informatica"

RUTA_SALIDA = (
    ROOT
    / "importaciones"
    / "informatica"
)

CODIGO_CFG = "C1-01_58_26"

RUTA_BD = ROOT / "db"


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Extrae preguntas desde un PDF "
            "de data_informatica."
        )
    )

    parser.add_argument(
        "pdf",
        help=(
            "Nombre o ruta del PDF. "
            "Ejemplo: preguntas_INF_def.pdf"
        ),
    )

    return parser.parse_args()


def resolver_pdf(
    valor,
):

    ruta = Path(
        valor
    )

    if ruta.exists():

        return ruta.resolve()

    ruta = (
        RUTA_DATOS
        / ruta.name
    )

    if ruta.exists():

        return ruta.resolve()

    raise FileNotFoundError(
        f"No existe el PDF: {valor}"
    )


def extraer_texto_pdf(
    ruta_pdf: Path,
) -> str:

    documento = fitz.open(
        ruta_pdf
    )

    try:

        paginas: list[str] = [
            str(
                pagina.get_text(
                    "text"
                )
            )
            for pagina in documento
        ]

    finally:

        documento.close()

    return "\n".join(
        paginas
    )


def limpiar_texto(
    texto,
):

    texto = texto.replace(
        "\r",
        "\n",
    )

    texto = texto.replace(
        "\u00a0",
        " ",
    )

    texto = re.sub(
        r"[ \t]+",
        " ",
        texto,
    )

    texto = re.sub(
        r"\n{3,}",
        "\n\n",
        texto,
    )

    return texto.strip()


def normalizar_opciones(
    texto,
):

    return re.sub(
        r"(?mi)^\s*([a-d])\)\s*",
        lambda coincidencia: (
            "\n"
            + coincidencia.group(1).upper()
            + ") "
        ),
        texto,
    )


def dividir_preguntas(
    texto,
):

    patron = re.compile(
        r"(?m)^\s*(\d{1,4})(?=\s|[¿A-ZÁÉÍÓÚÑ])\s*"
    )

    coincidencias = list(
        patron.finditer(
            texto
        )
    )

    bloques = []

    for indice, coincidencia in enumerate(
        coincidencias
    ):

        inicio = coincidencia.end()

        fin = (
            coincidencias[indice + 1].start()
            if indice + 1 < len(coincidencias)
            else len(texto)
        )

        bloques.append(
            {
                "numero_original": int(
                    coincidencia.group(1)
                ),
                "texto": texto[
                    inicio:fin
                ].strip(),
            }
        )

    return bloques


def extraer_pregunta(
    bloque,
):

    texto = normalizar_opciones(
        bloque["texto"]
    )

    coincidencias = list(
        re.finditer(
            r"(?m)^\s*([A-D])\)\s*",
            texto,
        )
    )

    if len(coincidencias) != 4:

        return None, (
            "No se detectaron exactamente "
            "cuatro opciones."
        )

    letras = [
        coincidencia.group(1)
        for coincidencia in coincidencias
    ]

    if letras != [
        "A",
        "B",
        "C",
        "D",
    ]:

        return None, (
            "Las opciones no siguen "
            "el orden A, B, C y D."
        )

    enunciado = texto[
        :coincidencias[0].start()
    ].strip()

    if not enunciado:

        return None, (
            "El enunciado está vacío."
        )

    opciones = {}

    for indice, coincidencia in enumerate(
        coincidencias
    ):

        inicio = coincidencia.end()

        fin = (
            coincidencias[indice + 1].start()
            if indice + 1 < len(coincidencias)
            else len(texto)
        )

        letra = coincidencia.group(1)

        opciones[
            letra
        ] = texto[
            inicio:fin
        ].strip()

    if any(
        not opciones[letra]
        for letra in (
            "A",
            "B",
            "C",
            "D",
        )
    ):

        return None, (
            "Alguna opción está vacía."
        )

    return {
        "numero_original": bloque[
            "numero_original"
        ],
        "enunciado": enunciado,
        "opciones": opciones,
    }, None


def extraer_preguntas(
    texto,
):

    bloques = dividir_preguntas(
        texto
    )

    preguntas = []
    incidencias = []

    for bloque in bloques:

        pregunta, error = extraer_pregunta(
            bloque
        )

        if error is not None:

            incidencias.append(
                {
                    "numero_original": bloque[
                        "numero_original"
                    ],
                    "motivo": error,
                    "texto": bloque[
                        "texto"
                    ],
                }
            )

            continue

        preguntas.append(
            pregunta
        )

    return preguntas, incidencias


def guardar_json(
    ruta_pdf,
    preguntas,
    incidencias,
):

    RUTA_SALIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta_json = (
        RUTA_SALIDA
        / f"{ruta_pdf.stem}_extraido.json"
    )

    contenido = {
        "pdf": ruta_pdf.name,
        "ruta_pdf": str(
            ruta_pdf.relative_to(
                ROOT
            )
        ).replace(
            "\\",
            "/",
        ),
        "preguntas_detectadas": len(
            preguntas
        ),
        "incidencias": incidencias,
        "preguntas": preguntas,
    }

    ruta_json.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return ruta_json

def abrir_conexion() -> sqlite3.Connection:

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def cargar_json(
    ruta_json: Path,
) -> dict:

    return json.loads(
        ruta_json.read_text(
            encoding="utf-8",
        )
    )

def obtener_convocatoria(
    conn: sqlite3.Connection,
) -> sqlite3.Row:

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (
            CODIGO_CFG,
        ),
    )

    convocatoria = cur.fetchone()

    if convocatoria is None:

        raise RuntimeError(
            f"No existe la convocatoria {CODIGO_CFG}."
        )

    return convocatoria




def main():

    argumentos = crear_argumentos()

    ruta_pdf = resolver_pdf(
        argumentos.pdf
    )

    texto = extraer_texto_pdf(
        ruta_pdf
    )

    texto = limpiar_texto(
        texto
    )

    preguntas, incidencias = (
        extraer_preguntas(
            texto
        )
    )

    ruta_json = guardar_json(
        ruta_pdf=ruta_pdf,
        preguntas=preguntas,
        incidencias=incidencias,
    )

    print()
    print("=" * 70)
    print("EXTRACCIÓN DE INFORMÁTICA")
    print("=" * 70)
    print(
        f"PDF................: {ruta_pdf.name}"
    )
    print(
        f"Preguntas..........: {len(preguntas)}"
    )
    print(
        f"Incidencias........: {len(incidencias)}"
    )
    print(
        f"JSON...............: {ruta_json}"
    )
    print("=" * 70)


if __name__ == "__main__":

    main()