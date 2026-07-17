"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : generar_simulacro.py
Ruta    : procesos/generar_simulacro.py

Objetivo:
    Generar y guardar un simulacro desde el banco de preguntas.

Entradas:
    - Distribución oficial.
    - Banco de la convocatoria.

Salidas:
    - Simulacro JSON y resumen de faltantes.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.constructor_simulacro

Utilizado por:
    - Ninguna.

Flujo:
    1. Construye el simulacro.
    2. Ordena preguntas.
    3. Guarda JSON.
    4. Muestra resumen.

Observaciones:
    - Ninguna.

==============================================================================
"""
import json
from datetime import datetime
from pathlib import Path

from core.constructor_simulacro import (
    construir_simulacro,
)
from core.normalizar_simulacro import (
    normalizar_datos_simulacro,
)

from core.render_pdf import (
    generar_pdf,
)

from core.render_soluciones_pdf import (
    generar_pdf_soluciones,
)
import argparse
import sqlite3


ROOT = Path(__file__).resolve().parents[1]

RUTA_SALIDA = ROOT / "simulacros"

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

def guardar_simulacro(
    contenido,
    nombre_archivo,
):

    RUTA_SALIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta = (
        RUTA_SALIDA
        / nombre_archivo
    )

    ruta.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return ruta

def mostrar_resumen(
    resultado,
    ruta,
):

    print()
    print("=" * 80)
    print("SIMULACRO GENERADO")
    print("=" * 80)

    print(
        f"Preguntas........: {resultado['total']}"
    )

    print(
        f"Completo.........: {resultado['completo']}"
    )

    print(
        f"Archivo..........: {ruta}"
    )

    if resultado["faltantes"]:

        print()
        print("FALTANTES")

        for dato in resultado["faltantes"]:

            destino = dato.get(
                "destino",
                (
                    "IA"
                    if dato["tipo_pregunta"]
                    == "ESPECIAL_INFORMATICA"
                    else "ERROR_BANCO"
                ),
            )

            print(
                f"{dato['tipo_pregunta']:24s} "
                f"Faltan {dato['faltan']} "
                f"-> {destino}"
            )

    faltantes_por_tema = resultado.get(
        "faltantes_por_tema",
        [],
    )

    faltantes_informatica = [
        dato
        for dato in faltantes_por_tema
        if dato["tipo_pregunta"]
        == "ESPECIAL_INFORMATICA"
    ]

    if faltantes_informatica:

        print()
        print("FALTANTES DE INFORMÁTICA POR TEMA")

        for dato in faltantes_informatica:

            print(
                f"Tema {dato['tema']:>2} "
                f"Faltan {dato['faltan']}"
            )

def construir_datos_simulacro(
    resultado,
):

    return {
        "total": resultado["total"],
        "completo": resultado["completo"],
        "faltantes": resultado["faltantes"],
        "faltantes_por_tema": resultado[
            "faltantes_por_tema"
        ],
        "compensaciones": resultado.get(
            "compensaciones",
            [],
        ),
        "resumen_bloques": resultado.get(
            "resumen_bloques",
            {},
        ),
        "preguntas": resultado["simulacro"],
    }

def obtener_siguiente_numero_simulacro(
    convocatoria_id,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                COALESCE(
                    MAX(numero),
                    0
                )
            FROM simulacros
            WHERE convocatoria_id = ?
            """,
            (
                convocatoria_id,
            ),
        )

        return (
            cur.fetchone()[0]
            + 1
        )

    finally:

        conn.close()

def obtener_datos_convocatoria(
    codigo_cfg,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    try:

        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
                cuerpo,
                numero,
                anio,
                codigo_cfg
            FROM convocatorias
            WHERE codigo_cfg = ?
            """,
            (
                codigo_cfg,
            ),
        )

        fila = cur.fetchone()

        if fila is None:

            raise ValueError(
                "No existe la convocatoria "
                f"{codigo_cfg}"
            )

        return {
            "id": int(fila["id"]),
            "cuerpo": str(fila["cuerpo"]),
            "numero": str(fila["numero"]),
            "anio": int(fila["anio"]),
            "codigo_cfg": str(
                fila["codigo_cfg"]
            ),
        }

    finally:

        conn.close()

def crear_registro_simulacro(
    convocatoria_id,
    numero_simulacro,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO simulacros (
                convocatoria_id,
                modo,
                estado,
                numero
            )
            VALUES (?, 'PDF', 'GENERADO', ?)
            """,
            (
                convocatoria_id,
                numero_simulacro,
            ),
        )

        simulacro_id = cur.lastrowid

        if simulacro_id is None:

            raise RuntimeError(
                "No se ha podido crear "
                "el registro del simulacro."
            )

        conn.commit()

        return int(
            simulacro_id
        )

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

def actualizar_rutas_simulacro(
    simulacro_id,
    ruta_json,
    ruta_pdf_preguntas,
    ruta_pdf_soluciones,
):

    conn = sqlite3.connect(
        RUTA_BD
    )

    try:

        conn.execute(
            """
            UPDATE simulacros
            SET
                ruta_json = ?,
                ruta_pdf_preguntas = ?,
                ruta_pdf_soluciones = ?,
                estado = 'GENERADO'
            WHERE id = ?
            """,
            (
                str(ruta_json),
                str(ruta_pdf_preguntas),
                str(ruta_pdf_soluciones),
                simulacro_id,
            ),
        )

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

def crear_nombres_simulacro(
    numero_simulacro,
    cuerpo,
):

    fecha = datetime.now().strftime(
        "%d%m%Y"
    )

    codigo_posicion = cuerpo.replace(
        "-",
        "_",
    )

    nombre_base = (
        f"SIM_{numero_simulacro:04d}_"
        f"{codigo_posicion}_"
        f"{fecha}"
    )

    return {
        "json": nombre_base + ".json",
        "preguntas": (
            nombre_base
            + "_PREGUNTAS.pdf"
        ),
        "soluciones": (
            nombre_base
            + "_SOLUCIONES.pdf"
        ),
    }

def generar_simulacro_convocatoria(
    codigo_cfg,
):

    datos_convocatoria = obtener_datos_convocatoria(
        codigo_cfg
    )

    numero_simulacro = (
        obtener_siguiente_numero_simulacro(
            datos_convocatoria["id"]
        )
    )

    simulacro_id = crear_registro_simulacro(
        convocatoria_id=datos_convocatoria[
            "id"
        ],
        numero_simulacro=numero_simulacro,
    )

    resultado = construir_simulacro(
    codigo_cfg=codigo_cfg,
    )

    datos_simulacro = construir_datos_simulacro(
        resultado
    )

    simulacro = normalizar_datos_simulacro(
        datos_simulacro
    )

    nombres = crear_nombres_simulacro(
        numero_simulacro=numero_simulacro,
        cuerpo=datos_convocatoria[
            "cuerpo"
        ],
    )

    ruta_json = guardar_simulacro(
        contenido=datos_simulacro,
        nombre_archivo=nombres["json"],
    )

    ruta_pdf_preguntas = (
        RUTA_SALIDA
        / nombres["preguntas"]
    )

    ruta_pdf_soluciones = (
        RUTA_SALIDA
        / nombres["soluciones"]
    )

    generar_pdf(
        simulacro=simulacro,
        ruta_pdf=ruta_pdf_preguntas,
    )

    generar_pdf_soluciones(
        simulacro=simulacro,
        ruta_pdf=ruta_pdf_soluciones,
    )

    actualizar_rutas_simulacro(
        simulacro_id=simulacro_id,
        ruta_json=ruta_json,
        ruta_pdf_preguntas=ruta_pdf_preguntas,
        ruta_pdf_soluciones=ruta_pdf_soluciones,
    )

    return {
        "resultado": resultado,
        "datos": datos_simulacro,
        "simulacro": simulacro,
        "ruta_json": ruta_json,
        "ruta_pdf_preguntas": (
            ruta_pdf_preguntas
        ),
        "ruta_pdf_soluciones": (
            ruta_pdf_soluciones
        ),
        "simulacro_id": simulacro_id,
        "numero_simulacro": (
            numero_simulacro
        ),
        "convocatoria": (
            datos_convocatoria
        ),
    }

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Genera un simulacro completo "
            "para una convocatoria."
        )
    )

    parser.add_argument(
        "codigo_cfg",
        help=(
            "Código de la convocatoria. "
            "Ejemplo: C1-01_58_26"
        ),
    )

    args = parser.parse_args()

    generado = generar_simulacro_convocatoria(
        args.codigo_cfg
    )

    mostrar_resumen(
        resultado=generado["resultado"],
        ruta=generado["ruta_json"],
    )

if __name__ == "__main__":

    main()