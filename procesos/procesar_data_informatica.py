"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : EN DESARROLLO

Archivo : procesar_data_informatica.py
Ruta    : procesos/procesar_data_informatica.py

Objetivo:
    Importar preguntas de informática, obtener mediante IA la respuesta
    correcta, clasificar el tema (15-23) e incorporarlas al banco de la
    convocatoria.

Entradas:
    - PDF de data_informatica.

Salidas:
    - preguntas_importadas
    - opciones_importadas
    - explicaciones_preguntas
    - banco_preguntas
    - banco_opciones

Modifica BD:
    Sí

Flujo:
    1. Detectar PDF nuevos.
    2. Extraer preguntas.
    3. Resolver respuesta y tema mediante IA.
    4. Importar.
    5. Incorporar al banco.

==============================================================================
"""

from pathlib import Path
import sqlite3
import hashlib
import json
import re

from core.huellas import calcular_huella
from core.openai_api import seleccionar_fragmento_json

ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

RUTA_DATOS = ROOT / "data_informatica"

CODIGO_CFG = "C1-01_58_26"

MODELO_IA = "gpt-5.4-mini"

TEMAS_INFORMATICA = {
    15: "Informática básica y hardware",
    16: "Windows 11",
    17: "Explorador de archivos de Windows 11",
    18: "Outlook de Microsoft 365",
    19: "Word de Microsoft 365",
    20: "Excel de Microsoft 365",
    21: "Teams de Microsoft 365",
    22: "Navegadores web",
    23: "Herramientas de Inteligencia Artificial",
}

def abrir_conexion():

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn

def calcular_hash_archivo(ruta):

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


def obtener_convocatoria_id(conn):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM convocatorias
        WHERE codigo_cfg = ?
        """,
        (
            CODIGO_CFG,
        ),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            f"No existe la convocatoria {CODIGO_CFG}"
        )

    return fila["id"]


def pdf_ya_importado(
    conn,
    ruta_pdf,
):

    hash_archivo = calcular_hash_archivo(
        ruta_pdf
    )

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM examenes
        WHERE hash_archivo = ?
        """,
        (
            hash_archivo,
        ),
    )

    return cur.fetchone() is not None

def extraer_texto_pdf(
    ruta_pdf,
):

    try:

        import fitz

    except ImportError as error:

        raise RuntimeError(
            "Falta PyMuPDF. Instálalo con: pip install pymupdf"
        ) from error

    documento = fitz.open(
        ruta_pdf
    )

    try:

        paginas = [
            pagina.get_text(
                "text"
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

    texto = re.sub(
        r"(?mi)^\s*\d+\.\s+",
        "\nPREGUNTA: ",
        texto,
    )

    texto = re.sub(
        r"\n{3,}",
        "\n\n",
        texto,
    )

    return texto.strip()

def normalizar_marcadores(
    texto,
):

    texto = texto.replace(
        "",
        "•",
    )

    texto = re.sub(
        r"(?mi)^\s*•?\s*Pregunta\s+\d+\s*:\s*",
        "\nPREGUNTA: ",
        texto,
    )

    texto = re.sub(
        r"(?mi)^\s*(\d+)\.\s+(?=¿)",
        r"\nPREGUNTA: ",
        texto,
    )

    texto = re.sub(
        r"(?mi)^\s*•?\s*([a-dA-D])\)\s*",
        lambda m: (
            "\n"
            + m.group(1).upper()
            + ") "
        ),
        texto,
    )

    return texto.strip()


def extraer_preguntas_texto(
    texto,
):

    texto = normalizar_marcadores(
        texto
    )

    bloques = re.split(
        r"(?m)^\s*PREGUNTA:\s*",
        texto,
    )

    preguntas = []

    for bloque in bloques:

        bloque = bloque.strip()

        if not bloque:
            continue

        coincidencias = list(
            re.finditer(
                r"(?m)^\s*([A-D])\)\s*",
                bloque,
            )
        )

        if len(coincidencias) < 4:
            continue

        enunciado = bloque[
            :coincidencias[0].start()
        ].strip()

        opciones = {}

        for indice, coincidencia in enumerate(
            coincidencias[:4]
        ):

            inicio = coincidencia.end()

            if indice + 1 < 4:

                fin = coincidencias[
                    indice + 1
                ].start()

            else:

                fin = len(
                    bloque
                )

            letra = coincidencia.group(1)

            opciones[letra] = bloque[
                inicio:fin
            ].strip()

        if (
            enunciado
            and set(opciones)
            == {"A", "B", "C", "D"}
        ):

            preguntas.append(
                {
                    "enunciado": enunciado,
                    "opciones": opciones,
                }
            )

    return preguntas

def construir_prompt_ia(
    pregunta,
):

    opciones = pregunta["opciones"]

    temas = "\n".join(
        f"{numero}: {titulo}"
        for numero, titulo
        in TEMAS_INFORMATICA.items()
    )

    return f"""
Analiza esta pregunta de informática para una oposición.

Debes:

1. Determinar la respuesta correcta.
2. Dar una explicación breve y precisa.
3. Clasificarla en uno de los temas 15 a 23.
4. Indicar tu confianza entre 0 y 1.

Temas:

{temas}

Pregunta:

{pregunta["enunciado"]}

Opciones:

A) {opciones["A"]}
B) {opciones["B"]}
C) {opciones["C"]}
D) {opciones["D"]}

Devuelve exclusivamente JSON válido:

{{
  "respuesta_correcta": "A|B|C|D",
  "explicacion_breve": "texto",
  "tema": 15,
  "confianza": 0.95
}}
""".strip()

def resolver_pregunta_ia(
    pregunta,
):

    prompt = construir_prompt_ia(
        pregunta
    )

    respuesta = seleccionar_fragmento_json(
        prompt=prompt,
        modelo=MODELO_IA,
        operacion="informatica_respuesta_tema",
    )

    letra = str(
        respuesta.get(
            "respuesta_correcta",
            "",
        )
    ).strip().upper()

    tema = respuesta.get(
        "tema"
    )

    confianza = float(
        respuesta.get(
            "confianza",
            0.0,
        )
    )

    explicacion = str(
        respuesta.get(
            "explicacion_breve",
            "",
        )
    ).strip()

    if letra not in {
        "A",
        "B",
        "C",
        "D",
    }:

        raise ValueError(
            "La IA no devolvió una respuesta "
            "correcta válida."
        )

    if tema not in TEMAS_INFORMATICA:

        tema = None

    return {
        "respuesta_correcta": letra,
        "explicacion_breve": explicacion,
        "tema": tema,
        "confianza": confianza,
    }

def obtener_parte_informatica_id(
    conn,
    convocatoria_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM partes_temario
        WHERE convocatoria_id = ?
          AND nombre = 'Especial-Informática'
        """,
        (
            convocatoria_id,
        ),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            "No existe la parte Especial-Informática."
        )

    return fila["id"]


def obtener_tema_id(
    conn,
    convocatoria_id,
    parte_id,
    numero_tema,
):

    if numero_tema is None:

        return None

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM temas
        WHERE convocatoria_id = ?
          AND parte_id = ?
          AND numero = ?
        """,
        (
            convocatoria_id,
            parte_id,
            numero_tema,
        ),
    )

    fila = cur.fetchone()

    return fila["id"] if fila else None


def insertar_examen(
    conn,
    convocatoria_id,
    ruta_pdf,
):

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
            calcular_hash_archivo(
                ruta_pdf
            ),
        ),
    )

    return cur.lastrowid

def insertar_pregunta_importada(
    conn,
    examen_id,
    numero,
    pregunta,
    resultado,
):

    cur = conn.cursor()

    estado = (
        "VALIDADA"
        if resultado["tema"] is not None
        else "A_REVISAR"
    )

    cur.execute(
        """
        INSERT INTO preguntas_importadas (
            examen_id,
            numero,
            enunciado,
            respuesta_correcta,
            parte_detectada,
            tema_detectado,
            estado_importacion,
            estado_validacion,
            tipo_pregunta,
            confianza_validacion,
            metodo_validacion
        )
        VALUES (
            ?, ?, ?, ?,
            'Especial-Informática',
            ?, 'IMPORTADA',
            ?, 'ESPECIAL_INFORMATICA',
            ?, 'IA'
        )
        """,
        (
            examen_id,
            numero,
            pregunta["enunciado"],
            resultado["respuesta_correcta"],
            resultado["tema"],
            estado,
            resultado["confianza"],
        ),
    )

    return cur.lastrowid


def insertar_opciones(
    conn,
    pregunta_importada_id,
    opciones,
):

    cur = conn.cursor()

    for letra in ("A", "B", "C", "D"):

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
                pregunta_importada_id,
                letra,
                opciones[letra],
            ),
        )


def insertar_explicacion(
    conn,
    pregunta_importada_id,
    pregunta,
    resultado,
):

    huella = calcular_huella(
        pregunta["enunciado"],
        pregunta["opciones"],
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO explicaciones_preguntas (
            pregunta_importada_id,
            huella_pregunta,
            explicacion_breve,
            modelo_ia
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            pregunta_importada_id,
            huella,
            resultado["explicacion_breve"],
            MODELO_IA,
        ),
    )


def insertar_en_banco(
    conn,
    convocatoria_id,
    parte_id,
    tema_id,
    pregunta_importada_id,
    pregunta,
    resultado,
):

    if tema_id is None:

        return

    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR IGNORE
        INTO banco_preguntas (

            pregunta_importada_id,
            convocatoria_id,
            parte_id,
            tema_id,

            enunciado,
            respuesta_correcta,

            estado

        )
        VALUES (

            ?, ?, ?, ?,
            ?, ?, 'VALIDADA'

        )
        """,
        (
            pregunta_importada_id,
            convocatoria_id,
            parte_id,
            tema_id,
            pregunta["enunciado"],
            resultado["respuesta_correcta"],
        ),
    )

    if cur.rowcount == 0:

        return

    banco_id = cur.lastrowid

    for letra in ("A", "B", "C", "D"):

        cur.execute(
            """
            INSERT INTO banco_opciones (

                banco_pregunta_id,
                letra,
                texto

            )
            VALUES (?, ?, ?)
            """,
            (
                banco_id,
                letra,
                pregunta["opciones"][letra],
            ),
        )

def procesar_pdf(
    conn,
    ruta_pdf,
):

    print()
    print("=" * 70)
    print(ruta_pdf.name)
    print("=" * 70)

    if pdf_ya_importado(
        conn,
        ruta_pdf,
    ):

        print("YA IMPORTADO")

        return {
            "importadas": 0,
            "banco": 0,
            "revisar": 0,
        }

    convocatoria_id = obtener_convocatoria_id(
        conn
    )

    parte_id = obtener_parte_informatica_id(
        conn,
        convocatoria_id,
    )

    examen_id = insertar_examen(
        conn,
        convocatoria_id,
        ruta_pdf,
    )

    texto = extraer_texto_pdf(
        ruta_pdf
    )

    texto = limpiar_texto(
        texto
    )

    preguntas = extraer_preguntas_texto(
        texto
    )

    print(
        f"Preguntas detectadas: {len(preguntas)}"
    )

    importadas = 0
    banco = 0
    revisar = 0

    for numero, pregunta in enumerate(
        preguntas,
        start=1,
    ):

        print()

        print(
            f"Pregunta {numero}"
        )

        resultado = resolver_pregunta_ia(
            pregunta
        )

        pregunta_importada_id = (
            insertar_pregunta_importada(
                conn,
                examen_id,
                numero,
                pregunta,
                resultado,
            )
        )

        insertar_opciones(
            conn,
            pregunta_importada_id,
            pregunta["opciones"],
        )

        insertar_explicacion(
            conn,
            pregunta_importada_id,
            pregunta,
            resultado,
        )

        tema_id = obtener_tema_id(
            conn,
            convocatoria_id,
            parte_id,
            resultado["tema"],
        )

        if tema_id is None:

            revisar += 1

            print(
                "→ A_REVISAR"
            )

        else:

            insertar_en_banco(
                conn,
                convocatoria_id,
                parte_id,
                tema_id,
                pregunta_importada_id,
                pregunta,
                resultado,
            )

            banco += 1

            print(
                f"→ Tema {resultado['tema']}"
            )

        importadas += 1

    conn.commit()

    return {
        "importadas": importadas,
        "banco": banco,
        "revisar": revisar,
    }


def main():

    print()

    print("=" * 70)
    print("IMPORTACIÓN INFORMÁTICA")
    print("=" * 70)

    conn = abrir_conexion()

    try:

        total_importadas = 0
        total_banco = 0
        total_revisar = 0

        pdfs = sorted(
            RUTA_DATOS.glob("*.pdf")
        )

        if not pdfs:

            print(
                "No existen PDF."
            )

            return

        for ruta_pdf in pdfs:

            resumen = procesar_pdf(
                conn,
                ruta_pdf,
            )

            total_importadas += resumen[
                "importadas"
            ]

            total_banco += resumen[
                "banco"
            ]

            total_revisar += resumen[
                "revisar"
            ]

    finally:

        conn.close()

    print()

    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Importadas........ {total_importadas}"
    )

    print(
        f"Banco............. {total_banco}"
    )

    print(
        f"A revisar......... {total_revisar}"
    )


if __name__ == "__main__":

    main()