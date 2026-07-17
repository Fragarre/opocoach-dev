"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : procesar_data_preguntas.py
Ruta    : procesos/procesar_data_preguntas.py

Objetivo:
    Extraer, importar, validar y clasificar todos los PDF nuevos existentes
    en data_preguntas.

Entradas:
    - PDF de data_preguntas, con una pregunta por página.

Salidas:
    - JSON extraídos en importaciones.
    - Preguntas incorporadas a SQLite.
    - Log de ejecución.

Modifica BD:
    Sí

Tablas afectadas:
    - examenes
    - preguntas_importadas
    - opciones_importadas

Utiliza:
    - procesos.extraer_pdf_imagenes
    - procesos.importar_json_extraido
    - procesos.clasificar_tipo_pregunta

Utilizado por:
    - Ejecución manual.

Flujo:
    1. Localiza los PDF de data_preguntas.
    2. Omite los PDF ya importados.
    3. Extrae cada PDF nuevo a JSON.
    4. Importa y valida las preguntas.
    5. Clasifica teoría, práctica e informática.
    6. Genera un resumen y un log.

Observaciones:
    - Continúa con el siguiente PDF aunque uno falle.
    - No reutiliza JSON parciales anteriores salvo que se indique --reutilizar-json.

==============================================================================
"""

import argparse
import hashlib
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"
RUTA_PDF = ROOT / "data_preguntas"
RUTA_IMPORTACIONES = ROOT / "importaciones"
RUTA_LOGS = ROOT / "logs"


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Procesa todos los PDF nuevos de data_preguntas."
        )
    )

    parser.add_argument(
        "--reutilizar-json",
        action="store_true",
        help=(
            "Reutiliza el JSON existente en vez de repetir "
            "la extracción."
        ),
    )

    return parser.parse_args()


def calcular_hash(ruta):

    sha256 = hashlib.sha256()

    with ruta.open("rb") as fichero:

        while True:

            bloque = fichero.read(
                1024 * 1024
            )

            if not bloque:
                break

            sha256.update(
                bloque
            )

    return sha256.hexdigest()


def pdf_ya_importado(ruta_pdf):

    hash_archivo = calcular_hash(
        ruta_pdf
    )

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id
            FROM examenes
            WHERE hash_archivo = ?
            """,
            (
                hash_archivo,
            ),
        )

        return cur.fetchone() is not None

    finally:

        conn.close()


def ejecutar(comando):

    inicio = time.time()

    proceso = subprocess.run(
        comando,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="replace",
    )

    return proceso, time.time() - inicio

def extraer_pdf(
    ruta_pdf,
    ruta_json,
):

    comando = [
        sys.executable,
        "-u",
        "-m",
        "procesos.extraer_pdf_imagenes",
        str(ruta_pdf),
        "--salida",
        str(ruta_json),
    ]

    inicio = time.time()

    proceso = subprocess.run(
        comando,
        cwd=ROOT,
        text=True,
    )

    return proceso, time.time() - inicio

def importar_json(
    ruta_json,
    ruta_pdf,
):

    comando = [
        sys.executable,
        "-m",
        "procesos.importar_json_extraido",
        str(ruta_json),
        str(ruta_pdf),
    ]

    return ejecutar(
        comando
    )


def clasificar_preguntas():

    comando = [
        sys.executable,
        "-m",
        "procesos.clasificar_tipo_pregunta",
        "--guardar",
    ]

    return ejecutar(
        comando
    )


def escribir_log(
    fichero,
    titulo,
    proceso,
):

    fichero.write(
        "\n"
        + "=" * 80
        + "\n"
    )

    fichero.write(
        titulo
        + "\n"
    )

    fichero.write(
        "-" * 80
        + "\n"
    )

    fichero.write(
        proceso.stdout or ""
    )

    fichero.write(
        proceso.stderr or ""
    )


def main():

    argumentos = crear_argumentos()

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: {RUTA_BD}"
        )

    RUTA_IMPORTACIONES.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUTA_LOGS.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_disponibles = sorted(
        RUTA_PDF.glob("*.pdf"),
        key=lambda ruta: ruta.name.lower(),
    )

    if not pdf_disponibles:

        print(
            "No existen PDF en data_preguntas."
        )

        return

    ruta_log = (
        RUTA_LOGS
        / (
            "procesar_data_preguntas_"
            f"{datetime.now():%Y%m%d_%H%M%S}.txt"
        )
    )

    resumen = {
        "pdf": len(pdf_disponibles),
        "omitidos": 0,
        "extraidos": 0,
        "importados": 0,
        "errores_extraccion": 0,
        "errores_importacion": 0,
    }

    inicio_total = time.time()

    print()
    print("=" * 80)
    print("PROCESAMIENTO DE DATA_PREGUNTAS")
    print("=" * 80)

    with ruta_log.open(
        "w",
        encoding="utf-8",
    ) as log:

        for ruta_pdf in pdf_disponibles:

            if pdf_ya_importado(
                ruta_pdf
            ):

                resumen["omitidos"] += 1

                print(
                    f"{ruta_pdf.name:<35}"
                    "YA IMPORTADO"
                )

                continue

            ruta_json = (
                RUTA_IMPORTACIONES
                / f"{ruta_pdf.stem}_extraido.json"
            )

            if (
                argumentos.reutilizar_json
                and ruta_json.exists()
            ):

                extraccion_correcta = True

                print(
                    f"{ruta_pdf.name:<35}"
                    "JSON EXISTENTE"
                )

            else:

                proceso, tiempo = extraer_pdf(
                    ruta_pdf=ruta_pdf,
                    ruta_json=ruta_json,
                )

                escribir_log(
                    fichero=log,
                    titulo=(
                        f"EXTRACCIÓN: {ruta_pdf.name}"
                    ),
                    proceso=proceso,
                )

                extraccion_correcta = (
                    proceso.returncode == 0
                    and ruta_json.exists()
                )

                if extraccion_correcta:

                    resumen["extraidos"] += 1

                    print(
                        f"{ruta_pdf.name:<35}"
                        f"EXTRAÍDO   {tiempo:7.1f}s"
                    )

                else:

                    resumen[
                        "errores_extraccion"
                    ] += 1

                    print(
                        f"{ruta_pdf.name:<35}"
                        "ERROR EXTRACCIÓN"
                    )

                    continue

            proceso, tiempo = importar_json(
                ruta_json=ruta_json,
                ruta_pdf=ruta_pdf,
            )

            escribir_log(
                fichero=log,
                titulo=(
                    f"IMPORTACIÓN: {ruta_pdf.name}"
                ),
                proceso=proceso,
            )

            if proceso.returncode == 0:

                resumen["importados"] += 1

                print(
                    f"{'':35}"
                    f"IMPORTADO  {tiempo:7.1f}s"
                )

            else:

                resumen[
                    "errores_importacion"
                ] += 1

                print(
                    f"{'':35}"
                    "ERROR IMPORTACIÓN"
                )

        proceso, tiempo = clasificar_preguntas()

        escribir_log(
            fichero=log,
            titulo="CLASIFICACIÓN FINAL",
            proceso=proceso,
        )

        clasificacion_correcta = (
            proceso.returncode == 0
        )

    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(
        f"PDF encontrados.........: {resumen['pdf']}"
    )
    print(
        f"Ya importados...........: {resumen['omitidos']}"
    )
    print(
        f"PDF extraídos...........: {resumen['extraidos']}"
    )
    print(
        f"PDF importados..........: {resumen['importados']}"
    )
    print(
        f"Errores de extracción...: "
        f"{resumen['errores_extraccion']}"
    )
    print(
        f"Errores de importación..: "
        f"{resumen['errores_importacion']}"
    )
    print(
        f"Clasificación final.....: "
        f"{'OK' if clasificacion_correcta else 'ERROR'}"
    )
    print(
        f"Tiempo total............: "
        f"{time.time() - inicio_total:0.1f} s"
    )
    print(
        f"Log.....................: {ruta_log}"
    )
    print("=" * 80)


if __name__ == "__main__":

    main()