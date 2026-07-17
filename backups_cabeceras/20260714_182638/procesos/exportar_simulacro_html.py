"""
Archivo: exportar_simulacro_html.py
Ruta: procesos/exportar_simulacro_html.py

Exporta un simulacro JSON a HTML imprimible.

Genera:
- examen sin respuestas;
- plantilla de soluciones al final.

No modifica la base de datos.
"""

import argparse
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_SIMULACROS = ROOT / "simulacros"


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description="Exporta un simulacro JSON a HTML."
    )

    parser.add_argument(
        "archivo",
        nargs="?",
        help=(
            "Ruta del simulacro JSON. "
            "Si se omite, utiliza el más reciente."
        ),
    )

    return parser.parse_args()


def buscar_simulacro_reciente():

    archivos = sorted(
        RUTA_SIMULACROS.glob("simulacro_*.json"),
        key=lambda ruta: ruta.stat().st_mtime,
        reverse=True,
    )

    if not archivos:

        raise FileNotFoundError(
            "No existen simulacros JSON en "
            f"{RUTA_SIMULACROS}"
        )

    return archivos[0]


def cargar_simulacro(ruta):

    contenido = json.loads(
        ruta.read_text(
            encoding="utf-8"
        )
    )

    preguntas = contenido.get(
        "preguntas"
    )

    if not isinstance(preguntas, list):

        raise ValueError(
            "El JSON no contiene una lista "
            "válida en 'preguntas'."
        )

    return contenido


def escapar(texto):

    return html.escape(
        str(texto or "")
    )


def nombre_bloque(tipo):

    nombres = {
        "ESPECIAL_TEORIA": "Especial · Teoría",
        "ESPECIAL_PRACTICA": "Especial · Práctica",
        "ESPECIAL_INFORMATICA": "Especial · Informática",
        "GENERAL": "General",
    }

    return nombres.get(
        tipo,
        tipo,
    )


def construir_pregunta(pregunta):

    numero = pregunta["numero_simulacro"]
    enunciado = escapar(
        pregunta["enunciado"]
    )

    opciones = pregunta["opciones"]

    lineas = [
        '<section class="pregunta">',
        f'<div class="numero">{numero}.</div>',
        '<div class="contenido">',
        f'<div class="enunciado">{enunciado}</div>',
        '<div class="opciones">',
    ]

    for letra in (
        "A",
        "B",
        "C",
        "D",
    ):

        texto = escapar(
            opciones[letra]
        )

        lineas.append(
            f'<div class="opcion">'
            f'<span class="letra">{letra})</span> '
            f'{texto}'
            f'</div>'
        )

    lineas.extend([
        "</div>",
        "</div>",
        "</section>",
    ])

    return "\n".join(
        lineas
    )


def construir_soluciones(preguntas):

    celdas = []

    for pregunta in preguntas:

        numero = pregunta[
            "numero_simulacro"
        ]

        respuesta = escapar(
            pregunta[
                "respuesta_correcta"
            ]
        )

        celdas.append(
            f"""
            <div class="solucion">
                <span>{numero}</span>
                <strong>{respuesta}</strong>
            </div>
            """
        )

    return "\n".join(
        celdas
    )


def construir_html(contenido):

    preguntas = contenido["preguntas"]

    bloques = []

    bloque_actual = None

    for pregunta in preguntas:

        bloque = pregunta[
            "tipo_pregunta"
        ]

        if bloque != bloque_actual:

            bloque_actual = bloque

            bloques.append(
                f"""
                <h2 class="bloque">
                    {escapar(nombre_bloque(bloque))}
                </h2>
                """
            )

        bloques.append(
            construir_pregunta(
                pregunta
            )
        )

    cuerpo_preguntas = "\n".join(
        bloques
    )

    soluciones = construir_soluciones(
        preguntas
    )

    total = len(
        preguntas
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Simulacro OpoNew</title>

<style>

@page {{
    size: A4;
    margin: 18mm 16mm;
}}

body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    line-height: 1.35;
    color: #111;
    max-width: 900px;
    margin: 0 auto;
}}

h1 {{
    text-align: center;
    margin-bottom: 4px;
}}

.subtitulo {{
    text-align: center;
    margin-bottom: 24px;
}}

.bloque {{
    margin-top: 28px;
    padding-bottom: 5px;
    border-bottom: 2px solid #222;
    page-break-after: avoid;
}}

.pregunta {{
    display: flex;
    gap: 8px;
    margin: 15px 0 20px 0;
    break-inside: avoid;
}}

.numero {{
    font-weight: bold;
    min-width: 28px;
}}

.contenido {{
    flex: 1;
}}

.enunciado {{
    font-weight: 600;
    margin-bottom: 9px;
}}

.opcion {{
    margin: 5px 0;
}}

.letra {{
    font-weight: bold;
}}

.salto-pagina {{
    page-break-before: always;
}}

.soluciones {{
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 8px;
    margin-top: 20px;
}}

.solucion {{
    border: 1px solid #777;
    padding: 6px;
    text-align: center;
}}

.solucion span {{
    display: block;
    font-size: 9pt;
}}

.solucion strong {{
    font-size: 13pt;
}}

@media print {{

    body {{
        max-width: none;
    }}

    .pregunta {{
        break-inside: avoid;
    }}
}}

</style>
</head>

<body>

<h1>SIMULACRO OPONEW</h1>

<div class="subtitulo">
    Total de preguntas: {total}
</div>

{cuerpo_preguntas}

<div class="salto-pagina"></div>

<h1>PLANTILLA DE RESPUESTAS</h1>

<div class="soluciones">
{soluciones}
</div>

</body>
</html>
"""


def main():

    argumentos = crear_argumentos()

    if argumentos.archivo:

        ruta_json = Path(
            argumentos.archivo
        )

        if not ruta_json.is_absolute():

            ruta_json = (
                ROOT
                / ruta_json
            )

    else:

        ruta_json = buscar_simulacro_reciente()

    if not ruta_json.exists():

        raise FileNotFoundError(
            f"No existe el archivo: {ruta_json}"
        )

    contenido = cargar_simulacro(
        ruta_json
    )

    contenido_html = construir_html(
        contenido
    )

    ruta_html = ruta_json.with_suffix(
        ".html"
    )

    ruta_html.write_text(
        contenido_html,
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("SIMULACRO EXPORTADO")
    print("=" * 80)
    print(
        f"JSON........: {ruta_json}"
    )
    print(
        f"HTML........: {ruta_html}"
    )


if __name__ == "__main__":

    main()