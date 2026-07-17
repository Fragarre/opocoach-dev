"""
Archivo: completar_simulacro_ia.py
Ruta: procesos/completar_simulacro_ia.py

Completa con IA los faltantes de Informática de un
simulacro JSON generado previamente.

No modifica la base de datos.
Guarda un nuevo archivo terminado en _completo.json.
"""

import argparse
import json
import random
import sqlite3
from pathlib import Path

from core.openai_api import (
    seleccionar_fragmento_json,
)


ROOT = Path(__file__).resolve().parents[1]

RUTA_SIMULACROS = ROOT / "simulacros"

RUTA_BD = ROOT / "db" / "oposiciones.sqlite3"

MODELO = "gpt-5.4-mini"

MAX_DOCUMENTACION = 18000


ORDEN_BLOQUES = (
    "ESPECIAL_TEORIA",
    "ESPECIAL_PRACTICA",
    "ESPECIAL_INFORMATICA",
    "GENERAL",
)


TOTALES_OFICIALES = {
    "ESPECIAL_TEORIA": 50,
    "ESPECIAL_PRACTICA": 15,
    "ESPECIAL_INFORMATICA": 15,
    "GENERAL": 30,
}


def crear_argumentos():

    parser = argparse.ArgumentParser(
        description=(
            "Completa con IA los faltantes de "
            "Informática de un simulacro."
        )
    )

    parser.add_argument(
        "archivo",
        nargs="?",
        help=(
            "Ruta del JSON. Si se omite, utiliza "
            "el simulacro incompleto más reciente."
        ),
    )

    return parser.parse_args()


def abrir_bd():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            f"No existe la base de datos: {RUTA_BD}"
        )

    conn = sqlite3.connect(
        RUTA_BD
    )

    conn.row_factory = sqlite3.Row

    return conn


def buscar_ultimo_simulacro():

    archivos = [
        ruta
        for ruta in RUTA_SIMULACROS.glob(
            "simulacro_*.json"
        )
        if not ruta.stem.endswith(
            "_completo"
        )
    ]

    archivos.sort(
        key=lambda ruta: ruta.stat().st_mtime,
        reverse=True,
    )

    if not archivos:

        raise FileNotFoundError(
            "No existe ningún simulacro incompleto."
        )

    return archivos[0]


def resolver_ruta(
    argumento,
):

    if argumento:

        ruta = Path(
            argumento
        )

        if not ruta.is_absolute():

            ruta = ROOT / ruta

    else:

        ruta = buscar_ultimo_simulacro()

    if not ruta.exists():

        raise FileNotFoundError(
            f"No existe el archivo: {ruta}"
        )

    return ruta


def cargar_simulacro(
    ruta,
):

    simulacro = json.loads(
        ruta.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        simulacro.get("preguntas"),
        list,
    ):

        raise ValueError(
            "El JSON no contiene una lista "
            "válida en 'preguntas'."
        )

    if not isinstance(
        simulacro.get(
            "faltantes_por_tema"
        ),
        list,
    ):

        raise ValueError(
            "El JSON no contiene "
            "'faltantes_por_tema'."
        )

    return simulacro


def obtener_tema(
    conn,
    numero,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            numero,
            titulo,
            descripcion
        FROM temas
        WHERE numero = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            numero,
        ),
    )

    fila = cur.fetchone()

    if fila is None:

        raise ValueError(
            f"No existe el tema {numero}."
        )

    return fila


def obtener_documentacion(
    conn,
    tema_id,
):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            d.id,
            d.nombre_archivo,
            d.titulo,
            d.texto_extraido
        FROM documentos d

        JOIN documentos_temas dt
            ON dt.documento_id = d.id

        WHERE
            dt.tema_id = ?

        ORDER BY d.id
        """,
        (
            tema_id,
        ),
    )

    documentos = cur.fetchall()

    if not documentos:

        raise ValueError(
            "No existen documentos asociados "
            f"al tema ID {tema_id}."
        )

    bloques = []

    for documento in documentos:

        bloques.append(
            "\n"
            + "=" * 70
            + "\n"
            + "DOCUMENTO: "
            + documento["nombre_archivo"]
            + "\n"
            + "=" * 70
        )

        cur.execute(
            """
            SELECT
                referencia,
                titulo_contexto,
                texto
            FROM fragmentos
            WHERE documento_id = ?
            ORDER BY orden
            """,
            (
                documento["id"],
            ),
        )

        fragmentos = cur.fetchall()

        if fragmentos:

            for fragmento in fragmentos:

                referencia = (
                    fragmento["referencia"]
                    or fragmento[
                        "titulo_contexto"
                    ]
                    or ""
                )

                bloques.append(
                    f"\n[{referencia}]\n"
                    f"{fragmento['texto']}"
                )

        elif documento["texto_extraido"]:

            bloques.append(
                "\n"
                + documento["texto_extraido"]
            )

    texto = "\n".join(
        bloques
    )

    if not texto.strip():

        raise ValueError(
            "La documentación del tema está vacía."
        )

    return texto[
        :MAX_DOCUMENTACION
    ]


def preguntas_existentes_tema(
    simulacro,
    tema,
):

    return [
        pregunta["enunciado"]
        for pregunta in simulacro["preguntas"]
        if (
            pregunta.get(
                "tipo_pregunta"
            )
            == "ESPECIAL_INFORMATICA"
            and pregunta.get(
                "tema"
            ) == tema
        )
    ]


def construir_prompt(
    tema,
    documentacion,
    existentes,
    cantidad,
):

    lista_existentes = "\n".join(
        f"- {enunciado}"
        for enunciado in existentes
    )

    return f"""
Eres especialista en elaboración de preguntas oficiales
para oposiciones de la Generalitat Valenciana.

Genera exactamente {cantidad} preguntas tipo test del
tema de Informática indicado.

TEMA
Número: {tema['numero']}
Título: {tema['titulo']}
Descripción: {tema['descripcion'] or ''}

REGLAS OBLIGATORIAS

- Cuatro opciones: A, B, C y D.
- Solo una opción correcta.
- La respuesta debe estar respaldada por la documentación.
- No inventes funciones, comandos ni características.
- Los distractores deben ser plausibles.
- No copies ni reformules las preguntas existentes.
- No menciones documentos ni material de estudio.
- Nivel y estilo de examen oficial.
- Devuelve únicamente JSON válido.
- No uses bloques Markdown.

PREGUNTAS EXISTENTES QUE NO DEBES REPETIR

{lista_existentes or '(ninguna)'}

DOCUMENTACIÓN AUTORIZADA

{documentacion}

FORMATO EXACTO

{{
  "preguntas": [
    {{
      "enunciado": "Texto",
      "opciones": {{
        "A": "Opción A",
        "B": "Opción B",
        "C": "Opción C",
        "D": "Opción D"
      }},
      "respuesta_correcta": "A",
      "justificacion": "Explicación breve"
    }}
  ]
}}
""".strip()


def validar_pregunta(
    pregunta,
):

    if not isinstance(
        pregunta,
        dict,
    ):

        raise ValueError(
            "La pregunta IA no es un objeto."
        )

    enunciado = str(
        pregunta.get(
            "enunciado",
            "",
        )
    ).strip()

    if not enunciado:

        raise ValueError(
            "La pregunta IA no tiene enunciado."
        )

    opciones = pregunta.get(
        "opciones"
    )

    if not isinstance(
        opciones,
        dict,
    ):

        raise ValueError(
            "La pregunta IA no contiene opciones."
        )

    opciones = {
        str(letra).strip().upper(): str(
            texto
        ).strip()
        for letra, texto in opciones.items()
    }

    if set(opciones) != {
        "A",
        "B",
        "C",
        "D",
    }:

        raise ValueError(
            "Las opciones IA no son exactamente "
            "A, B, C y D."
        )

    if any(
        not texto
        for texto in opciones.values()
    ):

        raise ValueError(
            "Existe una opción IA vacía."
        )

    respuesta = str(
        pregunta.get(
            "respuesta_correcta",
            "",
        )
    ).strip().upper()

    if respuesta not in opciones:

        raise ValueError(
            "La respuesta correcta IA no es válida."
        )

    return {
        "enunciado": enunciado,
        "opciones": opciones,
        "respuesta_correcta": respuesta,
        "texto_respuesta_correcta": opciones[
            respuesta
        ],
        "justificacion": str(
            pregunta.get(
                "justificacion",
                "",
            )
        ).strip(),
    }


def generar_preguntas(
    simulacro,
    tema_numero,
    cantidad,
):

    conn = abrir_bd()

    try:

        tema = obtener_tema(
            conn=conn,
            numero=tema_numero,
        )

        documentacion = obtener_documentacion(
            conn=conn,
            tema_id=tema["id"],
        )

    finally:

        conn.close()

    existentes = preguntas_existentes_tema(
        simulacro=simulacro,
        tema=tema_numero,
    )

    prompt = construir_prompt(
        tema=tema,
        documentacion=documentacion,
        existentes=existentes,
        cantidad=cantidad,
    )

    respuesta = seleccionar_fragmento_json(
        prompt=prompt,
        modelo=MODELO,
        operacion="simulacro_informatica",
    )

    preguntas_json = respuesta.get(
        "preguntas"
    )

    if not isinstance(
        preguntas_json,
        list,
    ):

        raise ValueError(
            "La IA no devolvió una lista "
            "de preguntas."
        )

    if len(
        preguntas_json
    ) != cantidad:

        raise ValueError(
            "La IA debía devolver "
            f"{cantidad} preguntas y devolvió "
            f"{len(preguntas_json)}."
        )

    resultado = []

    for indice, pregunta_json in enumerate(
        preguntas_json,
        start=1,
    ):

        pregunta = validar_pregunta(
            pregunta_json
        )

        pregunta.update(
            {
                "id": (
                    f"IA_INFORMATICA_"
                    f"{tema_numero}_{indice}"
                ),
                "examen_id": None,
                "numero_original": None,
                "numero_simulacro": None,
                "tipo_examen": "IA",
                "nombre_archivo": None,
                "origen": "IA",
                "tipo_pregunta": (
                    "ESPECIAL_INFORMATICA"
                ),
                "parte": (
                    "Especial-Informática"
                ),
                "tema": tema_numero,
                "norma": None,
                "articulo": None,
                "requiere_revision": True,
            }
        )

        resultado.append(
            pregunta
        )

    return resultado


def reconstruir_orden(
    preguntas,
):

    bloques = {
        bloque: []
        for bloque in ORDEN_BLOQUES
    }

    for pregunta in preguntas:

        bloque = pregunta.get(
            "tipo_pregunta"
        )

        if bloque not in bloques:

            raise ValueError(
                "Tipo de pregunta no reconocido: "
                f"{bloque!r}"
            )

        bloques[bloque].append(
            pregunta
        )

    random.shuffle(
        bloques["ESPECIAL_INFORMATICA"]
    )

    resultado = []

    for bloque in ORDEN_BLOQUES:

        resultado.extend(
            bloques[bloque]
        )

    for numero, pregunta in enumerate(
        resultado,
        start=1,
    ):

        pregunta[
            "numero_simulacro"
        ] = numero

    return resultado


def validar_totales(
    preguntas,
):

    totales = {
        bloque: 0
        for bloque in ORDEN_BLOQUES
    }

    for pregunta in preguntas:

        bloque = pregunta[
            "tipo_pregunta"
        ]

        totales[bloque] += 1

    if totales != TOTALES_OFICIALES:

        raise ValueError(
            "La distribución final no es correcta: "
            f"{totales}"
        )

    return totales


def completar_simulacro(
    ruta,
):

    simulacro = cargar_simulacro(
        ruta
    )

    faltantes = [
        dato
        for dato in simulacro[
            "faltantes_por_tema"
        ]
        if (
            dato.get(
                "tipo_pregunta"
            )
            == "ESPECIAL_INFORMATICA"
            and int(
                dato.get(
                    "faltan",
                    0,
                )
            ) > 0
        )
    ]

    if not faltantes:

        raise ValueError(
            "El simulacro no tiene faltantes "
            "de Informática."
        )

    nuevas = []

    for dato in faltantes:

        generadas = generar_preguntas(
            simulacro=simulacro,
            tema_numero=int(
                dato["tema"]
            ),
            cantidad=int(
                dato["faltan"]
            ),
        )

        nuevas.extend(
            generadas
        )

        simulacro[
            "preguntas"
        ].extend(
            generadas
        )

    preguntas = reconstruir_orden(
        simulacro["preguntas"]
    )

    totales = validar_totales(
        preguntas
    )

    simulacro["preguntas"] = preguntas
    simulacro["total"] = len(preguntas)
    simulacro["completo"] = True
    simulacro["preguntas_ia"] = len(nuevas)
    simulacro["faltantes"] = []
    simulacro["faltantes_por_tema"] = []

    simulacro["resumen_bloques"] = {
        bloque: {
            "objetivo": cantidad,
            "obtenidas": cantidad,
            "faltan": 0,
        }
        for bloque, cantidad
        in totales.items()
    }

    ruta_salida = ruta.with_name(
        ruta.stem
        + "_completo.json"
    )

    ruta_salida.write_text(
        json.dumps(
            simulacro,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return ruta_salida, simulacro


def main():

    argumentos = crear_argumentos()

    ruta = resolver_ruta(
        argumentos.archivo
    )

    ruta_salida, simulacro = (
        completar_simulacro(
            ruta
        )
    )

    print()
    print("=" * 80)
    print("SIMULACRO COMPLETADO")
    print("=" * 80)

    print(
        f"Origen.......: {ruta}"
    )

    print(
        f"Salida.......: {ruta_salida}"
    )

    print(
        f"Preguntas....: {simulacro['total']}"
    )

    print(
        f"IA...........: "
        f"{simulacro['preguntas_ia']}"
    )

    print(
        f"Completo.....: "
        f"{simulacro['completo']}"
    )


if __name__ == "__main__":

    main()