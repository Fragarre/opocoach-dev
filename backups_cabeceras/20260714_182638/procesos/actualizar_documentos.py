"""
Archivo: actualizar_documentos.py
Ruta: procesos/actualizar_documentos.py

Dependencias:
- argparse
- configparser
- hashlib
- pathlib
- re
- sqlite3
- PyMuPDF (fitz)

Funcionalidad:
Sincroniza de forma segura los documentos normativos del CFG con la BD.

El proceso:

- lee los PDF referenciados en el CFG;
- detecta documentos nuevos o sin texto extraído;
- extrae únicamente esos PDF;
- inserta o actualiza únicamente esos documentos;
- elimina únicamente sus fragmentos anteriores;
- fragmenta únicamente esos documentos;
- no modifica documentos ni fragmentos ya correctos;
- no modifica preguntas ni clasificaciones.

Por defecto funciona en modo prueba.
Para guardar es obligatorio utilizar --guardar.

Puede limitarse a un único PDF mediante --archivo.
"""

import argparse
import configparser
import hashlib
import re
import sqlite3
from pathlib import Path

import fitz
from core.temario import Temario

ROOT = Path(__file__).resolve().parents[1]

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"
RUTA_CFG = ROOT / "config" / "C1-01_58_26.cfg"
RUTA_PDF = ROOT / "data_leyes"

UMBRAL_FRAGMENTO = 3000

SUFIJOS_ARTICULO = (
    r"(?:bis|ter|quater|quinquies|sexies|"
    r"septies|octies|nonies|decies)"
)

PATRON_ARTICULO = re.compile(
    rf"^\s*Artículo\s+"
    rf"(?P<numero>\d+)"
    rf"(?:\s+(?P<sufijo>{SUFIJOS_ARTICULO}))?"
    rf"\.?\s*",
    re.MULTILINE,
)

PATRON_APARTADO = re.compile(
    r"^\s*\d+\.\s*",
)

PATRON_LETRA = re.compile(
    r"^\s*[a-z]\)\s*",
    re.IGNORECASE,
)


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Importa y fragmenta únicamente documentos "
            "nuevos o pendientes."
        )
    )

    parser.add_argument(
        "--guardar",
        action="store_true",
        help="Guarda los cambios en la base de datos.",
    )

    parser.add_argument(
        "--archivo",
        help=(
            "Procesa únicamente este nombre de archivo PDF."
        ),
    )

    parser.add_argument(
    "--forzar",
    action="store_true",
    help="Reprocesa documentos existentes aunque ya estén importados.",
    )

    return parser.parse_args()


def conectar():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def calcular_hash(
    ruta,
):

    sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:

        for bloque in iter(
            lambda: archivo.read(1024 * 1024),
            b"",
        ):

            sha256.update(
                bloque
            )

    return sha256.hexdigest()


def limpiar_texto(
    texto,
):

    texto = texto.replace(
        "\u00a0",
        " ",
    )

    texto = texto.replace(
        "\u00ad",
        "",
    )

    texto = texto.replace(
        "\r",
        "",
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


def extraer_pdf(
    ruta_pdf,
):

    documento = fitz.open(
        ruta_pdf
    )

    try:

        paginas = [
            pagina.get_text("text")
            for pagina in documento
        ]

    finally:

        documento.close()

    return limpiar_texto(
        "\n".join(paginas)
    )


def cargar_documentos_cfg():

    if not RUTA_CFG.exists():

        raise FileNotFoundError(
            f"No existe el CFG: "
            f"{RUTA_CFG.resolve()}"
        )

    config = configparser.ConfigParser(
        interpolation=None,
        delimiters=("=",),
        comment_prefixes=("#",),
        inline_comment_prefixes=("#",),
        strict=True,
    )

    config.optionxform = str

    with RUTA_CFG.open(
        "r",
        encoding="utf-8-sig",
    ) as archivo:

        config.read_file(
            archivo
        )

    documentos = set()

    for seccion in config.sections():

        if not seccion.startswith(
            "TEMARIO_"
        ):

            continue

        for _, valor in config.items(
            seccion
        ):

            partes = [
                elemento.strip()
                for elemento in valor.split("|")
                if elemento.strip()
            ]

            if len(partes) < 2:

                raise ValueError(
                    "Tema mal definido en "
                    f"[{seccion}]: {valor}"
                )

            for nombre_archivo in partes[1:]:

                if nombre_archivo.lower().endswith(
                    ".pdf"
                ):

                    documentos.add(
                        nombre_archivo
                    )

    return tuple(
        sorted(documentos)
    )


def localizar_articulos(
    texto,
):

    coincidencias = list(
        PATRON_ARTICULO.finditer(
            texto or ""
        )
    )

    articulos = []

    for indice, coincidencia in enumerate(
        coincidencias
    ):

        inicio = coincidencia.start()

        if indice + 1 < len(
            coincidencias
        ):

            final = coincidencias[
                indice + 1
            ].start()

        else:

            final = len(texto)

        numero = coincidencia.group(
            "numero"
        )

        sufijo = coincidencia.group(
            "sufijo"
        )

        if sufijo:

            sufijo = sufijo.lower()

        articulo = texto[
            inicio:final
        ].strip()

        if articulo:

            articulos.append(
                {
                    "numero": numero,
                    "sufijo": sufijo,
                    "texto": articulo,
                }
            )

    return articulos


def dividir_bloques(
    texto,
    patron,
):

    lineas = texto.splitlines()

    bloques = []
    actual = []

    for linea in lineas:

        if (
            patron.match(linea)
            and actual
        ):

            bloques.append(
                "\n".join(actual).strip()
            )

            actual = [
                linea
            ]

        else:

            actual.append(
                linea
            )

    if actual:

        bloques.append(
            "\n".join(actual).strip()
        )

    return [
        bloque
        for bloque in bloques
        if bloque
    ]


def referencia_articulo(
    articulo,
):

    referencia = (
        f"Artículo {articulo['numero']}"
    )

    if articulo["sufijo"]:

        referencia += (
            f" {articulo['sufijo']}"
        )

    return referencia


def fragmentar_articulo(
    articulo,
):

    texto = articulo[
        "texto"
    ].strip()

    referencia_base = (
        referencia_articulo(
            articulo
        )
    )

    if len(texto) <= UMBRAL_FRAGMENTO:

        return [
            {
                "tipo_fragmento": "ARTICULO",
                "referencia": referencia_base,
                "articulo": (
                    articulo["numero"]
                    + (
                        f" {articulo['sufijo']}"
                        if articulo["sufijo"]
                        else ""
                    )
                ),
                "apartado": None,
                "titulo_contexto": "",
                "texto": texto,
            }
        ]

    bloques = dividir_bloques(
        texto,
        PATRON_APARTADO,
    )

    if len(bloques) <= 1:

        bloques = [
            texto
        ]

    fragmentos = []

    for numero_bloque, bloque in enumerate(
        bloques,
        start=1,
    ):

        if len(bloque) <= UMBRAL_FRAGMENTO:

            fragmentos.append(
                {
                    "tipo_fragmento": "APARTADO",
                    "referencia": (
                        f"{referencia_base}, "
                        f"bloque {numero_bloque}"
                    ),
                    "articulo": (
                        articulo["numero"]
                        + (
                            f" {articulo['sufijo']}"
                            if articulo["sufijo"]
                            else ""
                        )
                    ),
                    "apartado": str(
                        numero_bloque
                    ),
                    "titulo_contexto": "",
                    "texto": bloque,
                }
            )

            continue

        subbloques = dividir_bloques(
            bloque,
            PATRON_LETRA,
        )

        if not subbloques:

            subbloques = [
                bloque
            ]

        for numero_subbloque, subbloque in enumerate(
            subbloques,
            start=1,
        ):

            fragmentos.append(
                {
                    "tipo_fragmento": "LETRA",
                    "referencia": (
                        f"{referencia_base}, "
                        f"bloque "
                        f"{numero_bloque}."
                        f"{numero_subbloque}"
                    ),
                    "articulo": (
                        articulo["numero"]
                        + (
                            f" {articulo['sufijo']}"
                            if articulo["sufijo"]
                            else ""
                        )
                    ),
                    "apartado": (
                        f"{numero_bloque}."
                        f"{numero_subbloque}"
                    ),
                    "titulo_contexto": "",
                    "texto": subbloque,
                }
            )

    return fragmentos


def eliminar_duplicados(
    fragmentos,
):

    vistos = set()
    resultado = []

    for fragmento in fragmentos:

        clave = (
            fragmento["referencia"],
            fragmento["texto"].strip(),
        )

        if clave in vistos:
            continue

        vistos.add(
            clave
        )

        resultado.append(
            fragmento
        )

    return resultado


def generar_fragmentos(
    texto,
):

    articulos = localizar_articulos(
        texto
    )

    fragmentos = []

    for articulo in articulos:

        fragmentos.extend(
            fragmentar_articulo(
                articulo
            )
        )

    return (
        articulos,
        eliminar_duplicados(
            fragmentos
        ),
    )


def obtener_documento_bd(
    conn,
    nombre_archivo,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            nombre_archivo,
            ruta,
            hash_archivo,
            texto_extraido
        FROM documentos
        WHERE nombre_archivo = ?
        """,
        (
            nombre_archivo,
        ),
    )

    return cur.fetchone()


def insertar_documento(
    conn,
    nombre_archivo,
    ruta_pdf,
    hash_archivo,
    texto,
):

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO documentos
        (
            nombre_archivo,
            tipo_documento,
            titulo,
            ruta,
            hash_archivo,
            texto_extraido
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            nombre_archivo,
            "NORMATIVA",
            nombre_archivo,
            str(
                ruta_pdf.relative_to(
                    ROOT
                )
            ),
            hash_archivo,
            texto,
        ),
    )

    return cur.lastrowid


def actualizar_documento(
    conn,
    documento_id,
    ruta_pdf,
    hash_archivo,
    texto,
):

    conn.execute(
        """
        UPDATE documentos
        SET
            ruta = ?,
            hash_archivo = ?,
            texto_extraido = ?
        WHERE id = ?
        """,
        (
            str(
                ruta_pdf.relative_to(
                    ROOT
                )
            ),
            hash_archivo,
            texto,
            documento_id,
        ),
    )

def actualizar_documentos_temas(
    conn,
    temario,
    documento_id,
    nombre_archivo,
):

    asociaciones = (
        temario.obtener_asociaciones_documento(
            nombre_archivo
        )
    )

    if not asociaciones:

        raise ValueError(
            "El documento no tiene asociación "
            f"en el temario: {nombre_archivo}"
        )

    conn.execute(
        """
        DELETE FROM documentos_temas
        WHERE documento_id = ?
        """,
        (
            documento_id,
        ),
    )

    cur = conn.cursor()

    for asociacion in asociaciones:

        cur.execute(
            """
            SELECT
                id,
                titulo
            FROM temas
            WHERE numero = ?
            """,
            (
                asociacion["tema"],
            ),
        )

        filas = cur.fetchall()

        titulo_cfg = re.sub(
            r"[^a-záéíóúüñ0-9]+",
            " ",
            asociacion["titulo_tema"].lower(),
        ).strip()

        coincidencias = []

        for candidata in filas:

            titulo_bd = re.sub(
                r"[^a-záéíóúüñ0-9]+",
                " ",
                candidata["titulo"].lower(),
            ).strip()

            if titulo_bd == titulo_cfg:

                coincidencias.append(
                    candidata
                )

        if len(coincidencias) != 1:

            raise ValueError(
                "No se ha podido identificar de forma única "
                f"el tema {asociacion['tema']}: "
                f"{asociacion['titulo_tema']}"
            )

        fila = coincidencias[0]

        cur.execute(
            """
            INSERT INTO documentos_temas
            (
                documento_id,
                tema_id
            )
            VALUES (?, ?)
            """,
            (
                documento_id,
                fila["id"],
            ),
        )
        
def reemplazar_fragmentos(
    conn,
    documento_id,
    fragmentos,
):

    conn.execute(
        """
        DELETE FROM fragmentos
        WHERE documento_id = ?
        """,
        (
            documento_id,
        ),
    )

    cur = conn.cursor()

    for orden, fragmento in enumerate(
        fragmentos,
        start=1,
    ):

        cur.execute(
            """
            INSERT INTO fragmentos
            (
                documento_id,
                tipo_fragmento,
                referencia,
                articulo,
                apartado,
                titulo_contexto,
                texto,
                orden
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                documento_id,
                fragmento[
                    "tipo_fragmento"
                ],
                fragmento[
                    "referencia"
                ],
                fragmento[
                    "articulo"
                ],
                fragmento[
                    "apartado"
                ],
                fragmento[
                    "titulo_contexto"
                ],
                fragmento[
                    "texto"
                ],
                orden,
            ),
        )


def seleccionar_documentos(
    conn,
    documentos_cfg,
    archivo=None,
    forzar=False,
):

    seleccionados = []

    for nombre_archivo in documentos_cfg:

        if (
            archivo is not None
            and nombre_archivo != archivo
        ):

            continue

        ruta_pdf = (
            RUTA_PDF
            / nombre_archivo
        )

        if not ruta_pdf.exists():

            raise FileNotFoundError(
                "El CFG referencia un PDF inexistente: "
                f"{ruta_pdf.resolve()}"
            )

        documento_bd = obtener_documento_bd(
            conn,
            nombre_archivo,
        )

        if documento_bd is None:

            estado = "NUEVO"

        elif not str(
            documento_bd[
                "texto_extraido"
            ] or ""
        ).strip():

            estado = "SIN_TEXTO"

        else:

            if not forzar:
                continue

            hash_actual = calcular_hash(
                ruta_pdf
            )

            if (
                documento_bd["hash_archivo"]
                != hash_actual
            ):

                estado = "MODIFICADO"

            else:

                continue

        seleccionados.append(
            {
                "nombre_archivo": nombre_archivo,
                "ruta_pdf": ruta_pdf,
                "documento_bd": documento_bd,
                "estado": estado,
            }
        )

    if (
        archivo is not None
        and not any(
            documento[
                "nombre_archivo"
            ] == archivo
            for documento in seleccionados
        )
    ):

        if archivo not in documentos_cfg:

            raise ValueError(
                "El archivo indicado no aparece "
                "en el CFG."
            )

    return seleccionados


def main():

    argumentos = crear_argumentos()

    temario = Temario()

    documentos_cfg = cargar_documentos_cfg()

    conn = conectar()

    procesados = 0
    total_articulos = 0
    total_fragmentos = 0

    try:

        seleccionados = seleccionar_documentos(
            conn=conn,
            documentos_cfg=documentos_cfg,
            archivo=argumentos.archivo,
            forzar=argumentos.forzar,
        )

        print()
        print("=" * 80)
        print("ACTUALIZACIÓN DE DOCUMENTOS")
        print("=" * 80)
        print(
            f"Documentos en CFG....: "
            f"{len(documentos_cfg)}"
        )
        print(
            f"Documentos pendientes: "
            f"{len(seleccionados)}"
        )
        print(
            f"Modo................: "
            f"{'GUARDAR' if argumentos.guardar else 'PRUEBA'}"
        )

        if not seleccionados:

            print()
            print(
                "No hay documentos nuevos o modificados."
            )

            return

        for documento in seleccionados:

            nombre_archivo = documento[
                "nombre_archivo"
            ]

            ruta_pdf = documento[
                "ruta_pdf"
            ]

            print()
            print("-" * 80)
            print(
                f"{nombre_archivo}"
            )
            print(
                f"Estado..............: "
                f"{documento['estado']}"
            )

            texto = extraer_pdf(
                ruta_pdf
            )

            if not texto:

                raise ValueError(
                    "No se ha podido extraer texto de "
                    f"{nombre_archivo}."
                )

            articulos, fragmentos = (
                generar_fragmentos(
                    texto
                )
            )

            if not articulos:

                raise ValueError(
                    "No se han detectado artículos en "
                    f"{nombre_archivo}."
                )

            if not fragmentos:

                raise ValueError(
                    "No se han generado fragmentos para "
                    f"{nombre_archivo}."
                )

            hash_archivo = calcular_hash(
                ruta_pdf
            )

            print(
                f"Caracteres...........: "
                f"{len(texto):,}"
            )
            print(
                f"Artículos............: "
                f"{len(articulos)}"
            )
            print(
                f"Fragmentos...........: "
                f"{len(fragmentos)}"
            )

            if argumentos.guardar:

                if documento[
                    "documento_bd"
                ] is None:

                    documento_id = insertar_documento(
                        conn=conn,
                        nombre_archivo=nombre_archivo,
                        ruta_pdf=ruta_pdf,
                        hash_archivo=hash_archivo,
                        texto=texto,
                    )

                else:

                    documento_id = documento[
                        "documento_bd"
                    ]["id"]

                    actualizar_documento(
                        conn=conn,
                        documento_id=documento_id,
                        ruta_pdf=ruta_pdf,
                        hash_archivo=hash_archivo,
                        texto=texto,
                    )

                reemplazar_fragmentos(
                    conn=conn,
                    documento_id=documento_id,
                    fragmentos=fragmentos,
                )

                actualizar_documentos_temas(
                    conn=conn,
                    temario=temario,
                    documento_id=documento_id,
                    nombre_archivo=nombre_archivo,
                )

            procesados += 1
            total_articulos += len(
                articulos
            )
            total_fragmentos += len(
                fragmentos
            )

        if argumentos.guardar:

            conn.commit()

        else:

            conn.rollback()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(
        f"Documentos procesados: "
        f"{procesados}"
    )
    print(
        f"Artículos detectados.: "
        f"{total_articulos}"
    )
    print(
        f"Fragmentos generados.: "
        f"{total_fragmentos}"
    )

    if argumentos.guardar:

        print(
            "Cambios guardados correctamente."
        )

    else:

        print(
            "MODO PRUEBA: no se ha modificado "
            "la base de datos."
        )


if __name__ == "__main__":
    main()