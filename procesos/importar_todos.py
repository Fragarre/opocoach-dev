"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

------------------------------------------------------------------------------
Archivo : importar_todos.py
Ruta    : procesos/importar_todos.py
------------------------------------------------------------------------------

Objetivo:
    Importar automáticamente todos los JSON de preguntas existentes en la
    carpeta de importaciones.

Entradas:
    - importaciones/*.json

Salidas:
    - Preguntas importadas.
    - Log de ejecución.

Modifica BD:
    Sí

Tablas afectadas:
    - examenes
    - preguntas
    - opciones

Utiliza:
    - importar_json_extraido.py

Utilizado por:
    - Ejecución manual.

Flujo:
    1. Busca todos los JSON.
    2. Los ordena.
    3. Ejecuta el importador.
    4. Continúa aunque haya errores.
    5. Genera un resumen.

Observaciones:
    - No contiene lógica de importación.
    - Reutiliza importar_json_extraido.py

==============================================================================
"""

from __future__ import annotations
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CARPETA_IMPORTACIONES = ROOT / "importaciones"

IMPORTADOR = (
    ROOT
    / "procesos"
    / "importar_json_extraido.py"
)

CARPETA_LOGS = ROOT / "logs"


# -----------------------------------------------------------------------------

PATRONES = {
    "procesadas": re.compile(r"Procesadas\.*:\s*(\d+)"),
    "importadas": re.compile(r"Importadas\.*:\s*(\d+)"),
    "duplicadas": re.compile(r"Duplicadas\.*:\s*(\d+)"),
    "validadas": re.compile(r"Validadas\.*:\s*(\d+)"),
    "rechazadas": re.compile(r"Rechazadas\.*:\s*(\d+)"),
}


def extraer_resumen(texto):

    if not texto:
        texto = ""

    datos = {}

    total_procesadas = 0
    total_importadas = 0
    total_duplicadas = 0
    total_validadas = 0
    total_rechazadas = 0

    for clave, patron in PATRONES.items():

        m = patron.search(texto)

        datos[clave] = int(m.group(1)) if m else 0

    return datos


def obtener_json():

    return sorted(
        CARPETA_IMPORTACIONES.glob("*_extraido.json"),
        key=lambda p: p.name.lower(),
    )


# -----------------------------------------------------------------------------


def convocatoria(nombre):

    return nombre.split("_")[0].upper()


# -----------------------------------------------------------------------------


def ejecutar(json_file):

    comando = [
        sys.executable,
        "-m",
        "procesos.importar_json_extraido",
        json_file.stem,
    ]

    inicio = time.time()

    proceso = subprocess.run(
        comando,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="replace",
    )

    tiempo = time.time() - inicio

    return proceso, tiempo

def main():

    CARPETA_LOGS.mkdir(
        exist_ok=True,
    )

    log = (
        CARPETA_LOGS
        /
        f"importacion_masiva_"
        f"{datetime.now():%Y%m%d_%H%M%S}.txt"
    )

    archivos = obtener_json()

    if not archivos:

        print(
            "No existen archivos *_extraido.json para importar."
        )

        return

    if not archivos:

        print(
            "No existen JSON para importar."
        )

        return

    inicio = time.time()

    total = len(archivos)

    ok = 0

    error = 0

    actual = None

    total_procesadas = 0
    total_importadas = 0
    total_duplicadas = 0
    total_validadas = 0
    total_rechazadas = 0

    with log.open(
        "w",
        encoding="utf-8",
    ) as salida:

        print()
        print("=" * 70)
        print("IMPORTACIÓN MASIVA")
        print("=" * 70)

        

        for json_file in archivos:

            grupo = convocatoria(
                json_file.stem
            )

            if grupo != actual:

                actual = grupo

                print()
                print(
                    "-" * 70
                )

                print(
                    f"Convocatoria {grupo}"
                )

                print(
                    "-" * 70
                )

            proceso, tiempo = ejecutar(
                json_file
            )

            resumen = extraer_resumen(
                proceso.stdout
            )

            total_procesadas += resumen["procesadas"]
            total_importadas += resumen["importadas"]
            total_duplicadas += resumen["duplicadas"]
            total_validadas += resumen["validadas"]
            total_rechazadas += resumen["rechazadas"]

            if proceso.returncode == 0:

                estado = "OK"

                ok += 1

            else:

                estado = "ERROR"

                error += 1

            print(
                f"{json_file.name:<35}"
                f"{estado:>8}"
                f"   {tiempo:6.2f}s"
            )

            salida.write(
                "\n"
                + "=" * 70
                + "\n"
            )

            salida.write(
                json_file.name
                + "\n"
            )

            salida.write(
                proceso.stdout
            )

            salida.write(
                proceso.stderr
            )

        print()
        
        print()
        print("=" * 70)

        print(f"Exámenes............. {total}")
        print(f"Correctos............ {ok}")
        print(f"Procesadas............ {total_procesadas}")
        print(f"Importadas............ {total_importadas}")
        print(f"Duplicadas............ {total_duplicadas}")
        print(f"Validadas............. {total_validadas}")
        print(f"Rechazadas............ {total_rechazadas}")
        print(f"Errores............... {error}")
        print(f"Tiempo................ {time.time() - inicio:0.1f} s")
        print(f"Log................... {log}")

        print("=" * 70)


# -----------------------------------------------------------------------------


if __name__ == "__main__":

    main()