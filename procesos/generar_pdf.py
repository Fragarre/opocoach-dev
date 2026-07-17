"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : generar_pdf.py
Ruta    : procesos/generar_pdf.py

Objetivo:
    Generar los PDF de examen y soluciones de un simulacro.

Entradas:
    - Simulacro explicado en JSON.

Salidas:
    - PDF del examen y PDF de soluciones.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.normalizar_simulacro
    - core.render_pdf
    - core.render_soluciones_pdf

Utilizado por:
    - Ninguna.

Flujo:
    1. Carga el simulacro.
    2. Normaliza.
    3. Genera ambos PDF.

Observaciones:
    - Ninguna.

==============================================================================
"""
from pathlib import Path

from core.normalizar_simulacro import (
    cargar_simulacro,
)

from core.render_pdf import (
    generar_pdf,
)

from core.render_soluciones_pdf import (
    generar_pdf_soluciones,
)


ROOT = Path(__file__).resolve().parents[1]

RUTA_SIMULACROS = ROOT / "simulacros"


def ultimo_simulacro_explicado():

    archivos = sorted(
        RUTA_SIMULACROS.glob(
            "*_completo_explicado.json"
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not archivos:

        raise FileNotFoundError(
            "No existe ningún simulacro "
            "completo y explicado."
        )

    return archivos[0]


def main():

    ruta_json = ultimo_simulacro_explicado()

    simulacro = cargar_simulacro(
        ruta_json
    )

    nombre_base = ruta_json.stem.removesuffix(
        "_explicado"
    )

    ruta_examen = ruta_json.with_name(
        nombre_base + ".pdf"
    )

    ruta_soluciones = ruta_json.with_name(
        nombre_base + "_soluciones.pdf"
    )

    generar_pdf(
        simulacro=simulacro,
        ruta_pdf=ruta_examen,
    )

    generar_pdf_soluciones(
        simulacro=simulacro,
        ruta_pdf=ruta_soluciones,
    )

    print()
    print("=" * 70)
    print("PDF GENERADOS")
    print("=" * 70)
    print(f"Examen.......: {ruta_examen}")
    print(f"Soluciones...: {ruta_soluciones}")


if __name__ == "__main__":

    main()