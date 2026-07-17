"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : extraer_pdf_imagenes.py
Ruta    : procesos/extraer_pdf_imagenes.py

Objetivo:
    Extraer preguntas desde un PDF compuesto por imágenes.

Entradas:
    - PDF con una pregunta por página.

Salidas:
    - JSON con preguntas extraídas e incidencias.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - Ninguna.

Flujo:
    1. Renderiza páginas.
    2. Envía imágenes a OpenAI.
    3. Valida estructura.
    4. Guarda JSON.

Observaciones:
    - Ninguna.

==============================================================================
"""
import argparse
import base64
import json
import re
import tempfile
from pathlib import Path
from core.openai_api import llamar_responses
import fitz



ROOT = Path(__file__).resolve().parents[1]

CARPETA_SALIDA = ROOT / "importaciones"

MODELO_DEFAULT = "gpt-5.4-mini"


PROMPT_EXTRACCION = """
Analiza esta imagen de una pregunta tipo test.

Devuelve exclusivamente un objeto JSON válido con esta estructura exacta:

{
  "numero": 1,
  "enunciado": "Texto completo del enunciado",
  "opciones": {
    "A": "Texto completo de la opción A",
    "B": "Texto completo de la opción B",
    "C": "Texto completo de la opción C",
    "D": "Texto completo de la opción D"
  },
  "respuesta_correcta": "A",
  "pie_completo": "Texto completo visible en el pie",
  "articulo": "27",
  "norma": "Constitución Española de 1978",
  "titulo_o_parte": "Título 1",
  "confianza_extraccion": 0.99,
  "incidencias": []
}

Reglas obligatorias:

1. Transcribe literalmente el enunciado y las cuatro opciones.
2. No corrijas errores jurídicos, ortográficos ni de redacción.
3. La respuesta correcta es la opción cuyo recuadro aparece resaltado en verde.
4. El pie normativo aparece normalmente en color azul en la parte inferior.
5. Extrae la norma y el artículo exclusivamente del pie.
6. Si no puedes leer un campo con seguridad:
   - usa null;
   - añade una explicación breve en "incidencias".
7. "respuesta_correcta" debe ser A, B, C, D o null.
8. "confianza_extraccion" debe estar entre 0 y 1.
9. No incluyas explicaciones fuera del JSON.
"""


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Extrae preguntas de un PDF de imágenes "
            "y genera un JSON para revisión."
        )
    )

    parser.add_argument(
        "pdf",
        help="Ruta del PDF que se va a procesar.",
    )

    parser.add_argument(
        "--modelo",
        default=MODELO_DEFAULT,
        help=(
            "Modelo de visión utilizado. "
            f"Por defecto: {MODELO_DEFAULT}"
        ),
    )

    parser.add_argument(
        "--desde",
        type=int,
        default=1,
        help="Primera página que se procesa. Por defecto: 1.",
    )

    parser.add_argument(
        "--hasta",
        type=int,
        default=None,
        help="Última página que se procesa.",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=170,
        help="Resolución de renderizado. Por defecto: 170.",
    )

    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta opcional del JSON de salida.",
    )

    return parser.parse_args()


def limpiar_json(
    texto,
):

    texto = str(
        texto or ""
    ).strip()

    texto = re.sub(
        r"^```(?:json)?\s*",
        "",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"\s*```$",
        "",
        texto,
    )

    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio == -1 or fin == -1:

        raise ValueError(
            "La respuesta no contiene un objeto JSON."
        )

    return texto[
        inicio:fin + 1
    ]


def imagen_a_data_url(
    ruta_imagen,
):

    contenido = ruta_imagen.read_bytes()

    codificado = base64.b64encode(
        contenido
    ).decode(
        "ascii"
    )

    return (
        "data:image/png;base64,"
        + codificado
    )


def renderizar_pagina(
    pagina,
    ruta_imagen,
    dpi,
):

    escala = dpi / 72

    matriz = fitz.Matrix(
        escala,
        escala,
    )

    pixmap = pagina.get_pixmap(
        matrix=matriz,
        alpha=False,
    )

    pixmap.save(
        str(ruta_imagen)
    )


def llamar_vision(
    cliente,
    ruta_imagen,
    modelo,
):

    data_url = imagen_a_data_url(
        ruta_imagen
    )

    respuesta, tiempo = llamar_responses(
        input_api=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": PROMPT_EXTRACCION,
                    },
                    {
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "high",
                    },
                ],
            }
        ],
        modelo=modelo,
        operacion="extraccion_pdf_imagen",
    )

    texto = limpiar_json(
        respuesta.output_text
    )

    datos = json.loads(
        texto
    )

    return datos, tiempo

def validar_estructura(
    datos,
    pagina_pdf,
):

    incidencias = datos.get(
        "incidencias"
    )

    if not isinstance(
        incidencias,
        list,
    ):

        incidencias = []

    datos["incidencias"] = incidencias

    numero = datos.get(
        "numero"
    )

    if numero is None:

        datos["numero"] = pagina_pdf

        incidencias.append(
            "No se detectó el número visible; "
            "se utiliza el número de página."
        )

    opciones = datos.get(
        "opciones"
    )

    if not isinstance(
        opciones,
        dict,
    ):

        opciones = {}

        datos["opciones"] = opciones

    for letra in (
        "A",
        "B",
        "C",
        "D",
    ):

        if not opciones.get(
            letra
        ):

            incidencias.append(
                f"No se extrajo la opción {letra}."
            )

            opciones[
                letra
            ] = None

    respuesta = datos.get(
        "respuesta_correcta"
    )

    if respuesta is not None:

        respuesta = str(
            respuesta
        ).strip().upper()

    if respuesta not in {
        "A",
        "B",
        "C",
        "D",
        None,
    }:

        incidencias.append(
            "La respuesta correcta detectada "
            "no es válida."
        )

        respuesta = None

    datos[
        "respuesta_correcta"
    ] = respuesta

    confianza = datos.get(
        "confianza_extraccion"
    )

    try:

        confianza = float(
            confianza
        )

    except (
        TypeError,
        ValueError,
    ):

        confianza = 0.0

    datos[
        "confianza_extraccion"
    ] = max(
        0.0,
        min(
            1.0,
            confianza,
        ),
    )

    datos[
        "pagina_pdf"
    ] = pagina_pdf

    datos[
        "extraccion_completa"
    ] = (
        bool(
            datos.get(
                "enunciado"
            )
        )
        and all(
            opciones.get(
                letra
            )
            for letra in (
                "A",
                "B",
                "C",
                "D",
            )
        )
        and respuesta
        in {
            "A",
            "B",
            "C",
            "D",
        }
        and bool(
            datos.get(
                "norma"
            )
        )
        and bool(
            datos.get(
                "articulo"
            )
        )
    )

    return datos


def calcular_ruta_salida(
    ruta_pdf,
    salida,
):

    if salida:

        ruta_salida = Path(
            salida
        )

        if not ruta_salida.is_absolute():

            ruta_salida = (
                ROOT
                / ruta_salida
            )

        return ruta_salida

    CARPETA_SALIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        CARPETA_SALIDA
        / (
            ruta_pdf.stem
            + "_extraido.json"
        )
    )


def extraer_pdf(
    ruta_pdf,
    modelo,
    pagina_desde,
    pagina_hasta,
    dpi,
    ruta_salida,
):

    if not ruta_pdf.exists():

        raise FileNotFoundError(
            f"No existe el PDF: {ruta_pdf}"
        )

    if pagina_desde <= 0:

        raise ValueError(
            "--desde debe ser mayor que cero."
        )

    documento = fitz.open(
        ruta_pdf
    )

    total_paginas = len(
        documento
    )

    if pagina_hasta is None:

        pagina_hasta = total_paginas

    pagina_hasta = min(
        pagina_hasta,
        total_paginas,
    )

    if pagina_desde > pagina_hasta:

        raise ValueError(
            "El intervalo de páginas no es válido."
        )

    preguntas = []

    with tempfile.TemporaryDirectory() as temporal:

        carpeta_temporal = Path(
            temporal
        )

        for numero_pagina in range(
            pagina_desde,
            pagina_hasta + 1,
        ):

            print()
            print("=" * 70)
            print(
                f"PÁGINA {numero_pagina} "
                f"DE {pagina_hasta}"
            )
            print("=" * 70)

            pagina = documento[
                numero_pagina - 1
            ]

            ruta_imagen = (
                carpeta_temporal
                / f"pagina_{numero_pagina:04d}.png"
            )

            try:

                renderizar_pagina(
                    pagina=pagina,
                    ruta_imagen=ruta_imagen,
                    dpi=dpi,
                )

                datos, tiempo = llamar_vision(
                    cliente=None,
                    ruta_imagen=ruta_imagen,
                    modelo=modelo,
                )

                datos = validar_estructura(
                    datos=datos,
                    pagina_pdf=numero_pagina,
                )

                datos[
                    "tiempo_extraccion"
                ] = round(
                    tiempo,
                    2,
                )

                datos[
                    "error_extraccion"
                ] = None

                print(
                    f"Número........: "
                    f"{datos.get('numero')}"
                )

                print(
                    f"Respuesta.....: "
                    f"{datos.get('respuesta_correcta')}"
                )

                print(
                    f"Norma.........: "
                    f"{datos.get('norma')}"
                )

                print(
                    f"Artículo......: "
                    f"{datos.get('articulo')}"
                )

                print(
                    f"Completa......: "
                    f"{datos.get('extraccion_completa')}"
                )

                print(
                    f"Tiempo........: "
                    f"{tiempo:.2f} s"
                )

            except Exception as error:

                datos = {
                    "pagina_pdf": numero_pagina,
                    "numero": numero_pagina,
                    "enunciado": None,
                    "opciones": {
                        "A": None,
                        "B": None,
                        "C": None,
                        "D": None,
                    },
                    "respuesta_correcta": None,
                    "pie_completo": None,
                    "articulo": None,
                    "norma": None,
                    "titulo_o_parte": None,
                    "confianza_extraccion": 0.0,
                    "incidencias": [
                        str(
                            error
                        )
                    ],
                    "extraccion_completa": False,
                    "tiempo_extraccion": None,
                    "error_extraccion": str(
                        error
                    ),
                }

                print(
                    f"ERROR.........: {error}"
                )

            preguntas.append(
                datos
            )

            contenido_salida = {
                "archivo_origen": ruta_pdf.name,
                "referencia_origen": ruta_pdf.stem,
                "total_paginas_pdf": total_paginas,
                "pagina_desde": pagina_desde,
                "pagina_hasta": pagina_hasta,
                "modelo_extraccion": modelo,
                "preguntas": preguntas,
            }

            ruta_salida.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            ruta_salida.write_text(
                json.dumps(
                    contenido_salida,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    documento.close()

    completas = sum(
        1
        for pregunta in preguntas
        if pregunta[
            "extraccion_completa"
        ]
    )

    print()
    print("=" * 70)
    print("EXTRACCIÓN FINALIZADA")
    print("=" * 70)
    print(
        f"Procesadas....: {len(preguntas)}"
    )
    print(
        f"Completas.....: {completas}"
    )
    print(
        f"A revisar.....: "
        f"{len(preguntas) - completas}"
    )
    print(
        f"Archivo.......: {ruta_salida}"
    )


def main():

    args = crear_argumentos()

    ruta_pdf = Path(
        args.pdf
    )

    if not ruta_pdf.is_absolute():

        ruta_pdf = (
            ROOT
            / ruta_pdf
        )

    ruta_salida = calcular_ruta_salida(
        ruta_pdf=ruta_pdf,
        salida=args.salida,
    )

    extraer_pdf(
        ruta_pdf=ruta_pdf,
        modelo=args.modelo,
        pagina_desde=args.desde,
        pagina_hasta=args.hasta,
        dpi=args.dpi,
        ruta_salida=ruta_salida,
    )


if __name__ == "__main__":

    main()