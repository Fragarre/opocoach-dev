"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : importar_json_extraido.py
Ruta    : procesos/importar_json_extraido.py

Objetivo:
    Incorporar a la convocatoria preguntas extraídas desde PDF de imágenes.

Entradas:
    - JSON extraído.
    - PDF de origen.
    - Código CFG.

Salidas:
    - Examen, preguntas y opciones importadas; informe de incidencias.

Modifica BD:
    Sí

Tablas afectadas:
    - examenes
    - opciones_importadas
    - preguntas_importadas

Utiliza:
    - core.huellas
    - core.normas
    - core.temario
    - core.validar_pie

Utilizado por:
    - Ninguna.

Flujo:
    1. Valida estructura.
    2. Elimina duplicados.
    3. Valida por pie.
    4. Inserta en SQLite.

Observaciones:
    - Ninguna.

==============================================================================
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from core.huellas import calcular_huella
from core.normas import cargar_normas
from core.temario import Temario
from core.validar_pie import validar_pie


ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

RUTA_IMPORTACIONES = ROOT / "importaciones"

CODIGO_CFG_DEFAULT = "C1-01_58_26"

def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Importa preguntas extraídas desde "
            "un PDF de imágenes."
        )
    )

    parser.add_argument(
        "json",
        help=(
            "Nombre o ruta del JSON. "
            "Ejemplos: C1_3, C1_3.json o importaciones/C1_3.json"
        ),
    )

    parser.add_argument(
        "pdf",
        nargs="?",
        default=None,
        help=(
            "PDF original. Si no se indica, se buscará automáticamente."
        ),
    )

    parser.add_argument(
        "--codigo-cfg",
        default=CODIGO_CFG_DEFAULT,
        help=(
            "Código de la convocatoria receptora. "
            f"Por defecto: {CODIGO_CFG_DEFAULT}"
        ),
    )

    return parser.parse_args()

def resolver_ruta(
    valor,
):

    ruta = Path(
        valor
    )

    if not ruta.is_absolute():

        ruta = ROOT / ruta

    return ruta.resolve()


def calcular_hash_archivo(
    ruta,
):

    sha256 = hashlib.sha256()

    with ruta.open(
        "rb"
    ) as fichero:

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


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: {RUTA_BD}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def cargar_json(
    ruta_json,
):

    if not ruta_json.exists():

        raise FileNotFoundError(
            f"No existe el JSON: {ruta_json}"
        )

    datos = json.loads(
        ruta_json.read_text(
            encoding="utf-8"
        )
    )

    preguntas = datos.get(
        "preguntas"
    )

    if not isinstance(
        preguntas,
        list,
    ):

        raise ValueError(
            "El JSON no contiene una lista "
            "válida en 'preguntas'."
        )

    if not preguntas:

        raise ValueError(
            "El JSON no contiene preguntas."
        )

    return datos


def limpiar_campo_opcional(
    valor,
):

    if valor is None:
        return None

    valor = str(
        valor
    ).strip()

    return valor or None


def preparar_pregunta(
    pregunta,
    indice,
):

    if not isinstance(
        pregunta,
        dict,
    ):

        raise ValueError(
            "La entrada no es un objeto JSON."
        )

    pagina = pregunta.get(
        "pagina_pdf",
        indice,
    )

    try:

        pagina = int(
            pagina
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "El número de página no es válido."
        )

    enunciado = limpiar_campo_opcional(
        pregunta.get(
            "enunciado"
        )
    )

    if not enunciado:

        raise ValueError(
            "La pregunta no tiene enunciado."
        )

    opciones = pregunta.get(
        "opciones"
    )

    if not isinstance(
        opciones,
        dict,
    ):

        raise ValueError(
            "La pregunta no contiene opciones."
        )

    opciones_limpias = {}

    for letra in (
        "A",
        "B",
        "C",
        "D",
    ):

        texto = limpiar_campo_opcional(
            opciones.get(
                letra
            )
        )

        if not texto:

            raise ValueError(
                f"No se ha extraído la opción {letra}."
            )

        opciones_limpias[
            letra
        ] = texto

    respuesta = limpiar_campo_opcional(
        pregunta.get(
            "respuesta_correcta"
        )
    )

    if respuesta is not None:

        respuesta = respuesta.upper()

    if respuesta not in {
        "A",
        "B",
        "C",
        "D",
    }:

        raise ValueError(
            "No se ha detectado una respuesta "
            "correcta válida."
        )

    incidencias = pregunta.get(
        "incidencias",
        [],
    )

    if not isinstance(
        incidencias,
        list,
    ):

        incidencias = [
            str(
                incidencias
            )
        ]

    return {
        "numero": pagina,
        "pagina_pdf": pagina,
        "enunciado": enunciado,
        "opciones": opciones_limpias,
        "respuesta_correcta": respuesta,
        "norma": limpiar_campo_opcional(
            pregunta.get(
                "norma"
            )
        ),
        "articulo": limpiar_campo_opcional(
            pregunta.get(
                "articulo"
            )
        ),
        "pie_completo": limpiar_campo_opcional(
            pregunta.get(
                "pie_completo"
            )
        ),
        "incidencias_extraccion": [
            str(incidencia)
            for incidencia in incidencias
        ],
    }


def obtener_convocatoria_id(
    conn,
    codigo_cfg,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id
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
            f"con código {codigo_cfg!r}."
        )

    return fila[
        "id"
    ]


def comprobar_pdf_no_importado(
    conn,
    hash_archivo,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            nombre_archivo
        FROM examenes
        WHERE hash_archivo = ?
        """,
        (
            hash_archivo,
        ),
    )

    fila = cur.fetchone()

    if fila is not None:

        raise ValueError(
            "El PDF ya está importado como examen "
            f"ID {fila['id']}: "
            f"{fila['nombre_archivo']}"
        )


def cargar_opciones_existentes(
    conn,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            pi.id AS pregunta_id,
            pi.enunciado,
            oi.letra,
            oi.texto
        FROM preguntas_importadas pi

        JOIN opciones_importadas oi
            ON oi.pregunta_importada_id = pi.id

        ORDER BY
            pi.id,
            oi.letra
        """
    )

    preguntas = {}

    for fila in cur.fetchall():

        pregunta_id = fila[
            "pregunta_id"
        ]

        dato = preguntas.setdefault(
            pregunta_id,
            {
                "enunciado": fila[
                    "enunciado"
                ],
                "opciones": {},
            },
        )

        dato["opciones"][
            fila["letra"]
        ] = fila["texto"]

    return preguntas


def cargar_huellas_existentes(
    conn,
):

    preguntas = cargar_opciones_existentes(
        conn
    )

    huellas = {}

    for pregunta_id, pregunta in preguntas.items():

        if set(
            pregunta["opciones"]
        ) != {
            "A",
            "B",
            "C",
            "D",
        }:

            continue

        huella = calcular_huella(
            pregunta["enunciado"],
            pregunta["opciones"],
        )

        huellas.setdefault(
            huella,
            pregunta_id,
        )

    return huellas


def ruta_relativa(
    ruta,
):

    try:

        return str(
            ruta.relative_to(
                ROOT
            )
        )

    except ValueError:

        return str(
            ruta
        )


def insertar_examen(
    conn,
    convocatoria_id,
    ruta_pdf,
    hash_archivo,
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
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            convocatoria_id,
            "APOYO",
            ruta_pdf.name,
            ruta_relativa(
                ruta_pdf
            ),
            hash_archivo,
        ),
    )

    return cur.lastrowid


def determinar_tipo_inicial(
    resultado_validacion,
):

    if (
        resultado_validacion[
            "estado_validacion"
        ]
        != "VALIDADA"
    ):

        return None

    parte = str(
        resultado_validacion.get(
            "parte"
        )
        or ""
    ).strip().lower()

    if parte == "general":

        return "GENERAL"

    if parte in {
        "especial-informática",
        "especial-informatica",
        "especial informática",
        "especial informatica",
    }:

        return "ESPECIAL_INFORMATICA"

    return None


def construir_motivo(
    pregunta,
    resultado_validacion,
):

    motivos = []

    if pregunta[
        "incidencias_extraccion"
    ]:

        motivos.append(
            "Incidencias de extracción: "
            + " | ".join(
                pregunta[
                    "incidencias_extraccion"
                ]
            )
        )

    motivo_validacion = str(
        resultado_validacion.get(
            "motivo"
        )
        or ""
    ).strip()

    if motivo_validacion:

        motivos.append(
            motivo_validacion
        )

    if not motivos:
        return None

    return " | ".join(
        motivos
    )


def insertar_pregunta(
    conn,
    examen_id,
    pregunta,
    resultado_validacion,
):

    tipo_pregunta = determinar_tipo_inicial(
        resultado_validacion
    )

    motivo = construir_motivo(
        pregunta=pregunta,
        resultado_validacion=resultado_validacion,
    )

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO preguntas_importadas (
            examen_id,
            numero,
            enunciado,
            respuesta_correcta,

            estado_importacion,
            estado_validacion,

            parte_detectada,
            tema_detectado,
            tipo_pregunta,

            norma_detectada,
            articulo_detectado,

            motivo_validacion,
            confianza_validacion,
            metodo_validacion
        )
        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?
        )
        """,
        (
            examen_id,
            pregunta["numero"],
            pregunta["enunciado"],
            pregunta["respuesta_correcta"],

            "IMPORTADA",
            resultado_validacion[
                "estado_validacion"
            ],

            resultado_validacion[
                "parte"
            ],
            resultado_validacion[
                "tema"
            ],
            tipo_pregunta,

            resultado_validacion[
                "codigo_norma"
            ],
            pregunta[
                "articulo"
            ],

            motivo,
            1.0,
            "PIE_DIRECTO",
        ),
    )

    return cur.lastrowid


def insertar_opciones(
    conn,
    pregunta_id,
    opciones,
):

    cur = conn.cursor()

    cur.executemany(
        """
        INSERT INTO opciones_importadas (
            pregunta_importada_id,
            letra,
            texto
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                pregunta_id,
                letra,
                opciones[
                    letra
                ],
            )
            for letra in (
                "A",
                "B",
                "C",
                "D",
            )
        ],
    )


def ruta_incidencias(
    ruta_pdf,
):

    RUTA_IMPORTACIONES.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        RUTA_IMPORTACIONES
        / (
            ruta_pdf.stem
            + "_incidencias.json"
        )
    )


def guardar_incidencias(
    ruta_pdf,
    incidencias,
    resumen,
):

    ruta = ruta_incidencias(
        ruta_pdf
    )

    contenido = {
        "archivo_origen": ruta_pdf.name,
        "resumen": resumen,
        "incidencias": incidencias,
    }

    ruta.write_text(
        json.dumps(
            contenido,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return ruta


def importar(
    ruta_json,
    ruta_pdf,
    codigo_cfg,
):

    if not ruta_pdf.exists():

        raise FileNotFoundError(
            f"No existe el PDF: {ruta_pdf}"
        )

    datos = cargar_json(
        ruta_json
    )

    temario = Temario()

    normas = cargar_normas()

    hash_archivo = calcular_hash_archivo(
        ruta_pdf
    )

    conn = abrir_conexion()

    resumen = {
        "procesadas": len(
            datos["preguntas"]
        ),
        "importadas": 0,
        "omitidas_error": 0,
        "duplicadas": 0,
        "validadas": 0,
        "a_revisar": 0,
        "rechazadas": 0,
    }

    incidencias = []

    try:

        convocatoria_id = obtener_convocatoria_id(
            conn=conn,
            codigo_cfg=codigo_cfg,
        )

        comprobar_pdf_no_importado(
            conn=conn,
            hash_archivo=hash_archivo,
        )

        huellas_existentes = cargar_huellas_existentes(
            conn
        )

        huellas_lote = set()

        preguntas_preparadas = []

        for indice, pregunta_json in enumerate(
            datos["preguntas"],
            start=1,
        ):

            pagina = pregunta_json.get(
                "pagina_pdf",
                indice,
            )

            try:

                pregunta = preparar_pregunta(
                    pregunta=pregunta_json,
                    indice=indice,
                )

            except Exception as error:

                resumen[
                    "omitidas_error"
                ] += 1

                incidencias.append(
                    {
                        "pagina_pdf": pagina,
                        "tipo": "ERROR_EXTRACCION",
                        "motivo": str(
                            error
                        ),
                    }
                )

                continue

            huella = calcular_huella(
                pregunta["enunciado"],
                pregunta["opciones"],
            )

            if huella in huellas_existentes:

                resumen[
                    "duplicadas"
                ] += 1

                incidencias.append(
                    {
                        "pagina_pdf": pregunta[
                            "pagina_pdf"
                        ],
                        "tipo": "DUPLICADA_BD",
                        "pregunta_existente_id": (
                            huellas_existentes[
                                huella
                            ]
                        ),
                        "enunciado": pregunta[
                            "enunciado"
                        ],
                    }
                )

                continue

            if huella in huellas_lote:

                resumen[
                    "duplicadas"
                ] += 1

                incidencias.append(
                    {
                        "pagina_pdf": pregunta[
                            "pagina_pdf"
                        ],
                        "tipo": "DUPLICADA_LOTE",
                        "enunciado": pregunta[
                            "enunciado"
                        ],
                    }
                )

                continue

            huellas_lote.add(
                huella
            )

            preguntas_preparadas.append(
                pregunta
            )

        if not preguntas_preparadas:

            raise ValueError(
                "No existe ninguna pregunta nueva "
                "y válida para importar."
            )

        examen_id = insertar_examen(
            conn=conn,
            convocatoria_id=convocatoria_id,
            ruta_pdf=ruta_pdf,
            hash_archivo=hash_archivo,
        )

        for pregunta in preguntas_preparadas:

            referencia_normativa = (
                pregunta.get("norma")
                or pregunta.get("pie_completo")
                or pregunta.get("enunciado")
            )

            resultado_validacion = validar_pie(
                norma=referencia_normativa,
                articulo=pregunta["articulo"],
                temario=temario,
                normas=normas,
            )

            estado = resultado_validacion[
                "estado_validacion"
            ]

            if estado == "VALIDADA":

                resumen[
                    "validadas"
                ] += 1

            elif estado == "A_REVISAR":

                resumen[
                    "a_revisar"
                ] += 1

            elif estado == "RECHAZADA":

                resumen[
                    "rechazadas"
                ] += 1

            else:

                raise ValueError(
                    "Estado de validación no reconocido: "
                    f"{estado!r}"
                )

            pregunta_id = insertar_pregunta(
                conn=conn,
                examen_id=examen_id,
                pregunta=pregunta,
                resultado_validacion=(
                    resultado_validacion
                ),
            )

            insertar_opciones(
                conn=conn,
                pregunta_id=pregunta_id,
                opciones=pregunta[
                    "opciones"
                ],
            )

            resumen[
                "importadas"
            ] += 1

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    ruta_informe = guardar_incidencias(
        ruta_pdf=ruta_pdf,
        incidencias=incidencias,
        resumen=resumen,
    )

    print()
    print("=" * 80)
    print("IMPORTACIÓN FINALIZADA")
    print("=" * 80)

    print(
        f"Examen ID...........: {examen_id}"
    )

    print(
        f"PDF.................: {ruta_pdf.name}"
    )

    print(
        f"Referencia..........: "
        f"{datos.get('referencia_origen', ruta_pdf.stem)}"
    )

    print(
        f"Procesadas..........: {resumen['procesadas']}"
    )

    print(
        f"Importadas..........: {resumen['importadas']}"
    )

    print(
        f"Omitidas por error..: "
        f"{resumen['omitidas_error']}"
    )

    print(
        f"Duplicadas..........: {resumen['duplicadas']}"
    )

    print(
        f"Validadas...........: {resumen['validadas']}"
    )

    print(
        f"A revisar...........: {resumen['a_revisar']}"
    )

    print(
        f"Rechazadas..........: {resumen['rechazadas']}"
    )

    print(
        f"Informe..............: {ruta_informe}"
    )


def main():

    argumentos = crear_argumentos()

    ruta_json = Path(argumentos.json)

    if not ruta_json.exists():

        if ruta_json.suffix == "":
            ruta_json = (
                Path("importaciones")
                / f"{ruta_json.name}.json"
            )

        else:
            ruta_json = (
                Path("importaciones")
                / ruta_json.name
            )

    ruta_json = resolver_ruta(
        ruta_json
    )

    if argumentos.pdf is None:

        nombre_base = ruta_json.stem

        if nombre_base.endswith("_extraido"):

            nombre_base = nombre_base[
                :-len("_extraido")
            ]

        ruta_pdf = resolver_ruta(
            Path("data_preguntas")
            / f"{nombre_base}.pdf"
        )

    else:

        ruta_pdf = resolver_ruta(
            argumentos.pdf
        )

    if not ruta_pdf.exists():

        raise FileNotFoundError(
            f"No existe el PDF: {ruta_pdf}"
        )

    importar(
        ruta_json=ruta_json,
        ruta_pdf=ruta_pdf,
        codigo_cfg=argumentos.codigo_cfg,
    )

if __name__ == "__main__":

    main()