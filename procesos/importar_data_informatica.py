"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : EN DESARROLLO

Archivo : importar_data_informatica.py
Ruta    : procesos/importar_data_informatica.py

Objetivo:
    Importar preguntas de informática ya clasificadas como conocimiento
    permanente.

Entradas:
    - JSON *_clasificado.json.

Salidas:
    - examenes
    - preguntas_importadas
    - opciones_importadas
    - explicaciones_preguntas

Modifica BD:
    Sí

Tablas afectadas:
    - examenes
    - preguntas_importadas
    - opciones_importadas
    - explicaciones_preguntas

Flujo:
    1. Comprobar la idempotencia del PDF.
    2. Crear o localizar el examen origen.
    3. Importar preguntas.
    4. Importar opciones.
    5. Importar explicaciones.

Observaciones:
    - No evalúa convocatorias.
    - No actualiza el banco.
    - La clasificación por convocatoria se realiza posteriormente mediante
      evaluar_convocatoria.py.

==============================================================================
"""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from core.huellas import calcular_huella


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

RUTA_IMPORTACIONES = (
    ROOT
    / "importaciones"
    / "informatica"
)

CODIGO_CFG = "C1-01_58_26"

def obtener_convocatoria_id(
    conn: sqlite3.Connection,
) -> int:

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (CODIGO_CFG,),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            f"No existe la convocatoria {CODIGO_CFG}"
        )

    return int(fila["id"])


def calcular_hash_archivo(
    ruta: Path,
) -> str:

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


def existe_examen(
    conn: sqlite3.Connection,
    hash_pdf: str,
) -> bool:

    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1
        FROM examenes
        WHERE hash_archivo = ?
        LIMIT 1
        """,
        (
            hash_pdf,
        ),
    )

    return cur.fetchone() is not None

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

def obtener_pdf_json(
    datos: dict,
) -> Path:

    ruta = Path(
        datos["ruta_pdf"]
    )

    if not ruta.exists():

        raise FileNotFoundError(
            f"No existe el PDF: {ruta}"
        )

    return ruta.resolve()

def crear_argumentos():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "json",
        help="JSON *_clasificado.json",
    )

    return parser.parse_args()

def resolver_json(
    valor: str,
) -> Path:

    ruta = Path(valor)

    if ruta.exists():
        return ruta.resolve()

    ruta = (
        RUTA_IMPORTACIONES
        / Path(valor).name
    )

    if ruta.exists():
        return ruta.resolve()

    raise FileNotFoundError(
        f"No existe el JSON: {valor}"
    )

def insertar_examen(
    conn: sqlite3.Connection,
    convocatoria_id: int,
    ruta_pdf: Path,
    hash_pdf: str,
) -> int:

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO examenes (
            convocatoria_id,
            tipo_examen,
            nombre_archivo,
            ruta,
            hash_archivo
        )
        VALUES (?, 'APOYO', ?, ?, ?)
        """,
        (
            convocatoria_id,
            ruta_pdf.name,
            str(
                ruta_pdf.relative_to(ROOT)
            ),
            hash_pdf,
        ),
    )

    examen_id = cur.lastrowid

    if examen_id is None:

        raise RuntimeError(
            "No se pudo obtener el id del examen."
        )

    return examen_id

def insertar_pregunta(
    conn: sqlite3.Connection,
    examen_id: int,
    pregunta: dict,
) -> int:

    clasificacion = pregunta["clasificacion"]

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO preguntas_importadas (
            examen_id,
            numero,
            enunciado,
            respuesta_correcta,
            estado_importacion,
            norma_detectada,
            articulo_detectado,
            materia_detectada
        )
        VALUES (?, ?, ?, ?, 'IMPORTADA', NULL, NULL, ?)
        """,
        (
            examen_id,
            pregunta["numero_original"],
            pregunta["enunciado"],
            clasificacion["respuesta_correcta"],
            clasificacion["materia"],
        ),
    )

    pregunta_id = cur.lastrowid

    if pregunta_id is None:

        raise RuntimeError(
            "No se pudo obtener el id de la pregunta."
        )

    return pregunta_id

def insertar_opciones(
    conn: sqlite3.Connection,
    pregunta_id: int,
    opciones: dict,
) -> None:

    cur = conn.cursor()

    for letra in (
        "A",
        "B",
        "C",
        "D",
    ):

        cur.execute(
            """
            INSERT INTO opciones_importadas (
                pregunta_importada_id,
                letra,
                texto
            )
            VALUES (?, ?, ?)
            """,
            (
                pregunta_id,
                letra,
                opciones[letra],
            ),
        )

def insertar_explicacion(
    conn: sqlite3.Connection,
    pregunta_id: int,
    pregunta: dict,
) -> None:

    clasificacion = pregunta["clasificacion"]

    explicacion = str(
        clasificacion.get(
            "explicacion_breve",
            "",
        )
    ).strip()

    if not explicacion:
        return

    huella = calcular_huella(
        pregunta["enunciado"],
        pregunta["opciones"],
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO explicaciones_preguntas (
            pregunta_importada_id,
            huella_pregunta,
            explicacion_breve,
            modelo_ia
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            pregunta_id,
            huella,
            explicacion,
            "gpt-5.4-mini",
        ),
    )

def main():

    argumentos = crear_argumentos()

    ruta_json = resolver_json(
        argumentos.json
    )

    datos = cargar_json(
        ruta_json
    )

    ruta_pdf = obtener_pdf_json(
        datos
    )

    hash_pdf = calcular_hash_archivo(
        ruta_pdf
    )

    conn = abrir_conexion()

    try:

        print()
        print("=" * 70)
        print("IMPORTACIÓN INFORMÁTICA")
        print("=" * 70)
        print(f"JSON.............: {ruta_json.name}")
        print(f"PDF..............: {ruta_pdf.name}")
        print(f"Hash.............: {hash_pdf}")

        if existe_examen(
            conn,
            hash_pdf,
        ):

            print()
            print("El PDF ya está importado.")
            return

        print()
        print("El PDF todavía no está importado.")
        convocatoria_id = obtener_convocatoria_id(
            conn
        )

        examen_id = insertar_examen(
            conn=conn,
            convocatoria_id=convocatoria_id,
            ruta_pdf=ruta_pdf,
            hash_pdf=hash_pdf,
        )

        importadas = 0

        for pregunta in datos["preguntas"]:

            pregunta_id = insertar_pregunta(
                conn=conn,
                examen_id=examen_id,
                pregunta=pregunta,
            )

            insertar_opciones(
                conn=conn,
                pregunta_id=pregunta_id,
                opciones=pregunta["opciones"],
            )

            insertar_explicacion(
                conn=conn,
                pregunta_id=pregunta_id,
                pregunta=pregunta,
            )

            importadas += 1

        conn.commit()

        print(
            f"Preguntas importadas: {importadas}"
        )

        print(
            f"Examen ID........: {examen_id}"
        )

    except Exception:

        conn.rollback()
        raise

    finally:
            conn.close()

if __name__ == "__main__":

    main()