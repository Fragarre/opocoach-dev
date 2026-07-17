"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : normalizar_cabeceras.py
Ruta    : procesos/normalizar_cabeceras.py

Objetivo:
    Auditar el cumplimiento de la cabecera estándar en los scripts.

Entradas:
    - Scripts Python del proyecto.

Salidas:
    - docs/CABECERAS_PENDIENTES.md.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - Ninguna.

Flujo:
    1. Lee docstrings.
    2. Comprueba campos.
    3. Genera informe.

Observaciones:
    - Ninguna.

==============================================================================
"""
import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUTA_INFORME = (
    ROOT
    / "docs"
    / "CABECERAS_PENDIENTES.md"
)

CARPETAS_CODIGO = (
    ROOT / "core",
    ROOT / "procesos",
    ROOT / "render",
)

CAMPOS_OBLIGATORIOS = (
    "Proyecto",
    "Tipo",
    "Estado",
    "Archivo",
    "Ruta",
    "Objetivo",
    "Entradas",
    "Salidas",
    "Modifica BD",
    "Tablas afectadas",
    "Utiliza",
    "Utilizado por",
    "Flujo",
    "Observaciones",
)

TIPOS_VALIDOS = {
    "Core",
    "Proceso",
    "Utilidad",
}

ESTADOS_VALIDOS = {
    "OK",
    "REV",
    "DES",
    "OBS",
}


def obtener_scripts():

    scripts = []

    for carpeta in CARPETAS_CODIGO:

        if not carpeta.exists():
            continue

        scripts.extend(
            ruta
            for ruta in carpeta.rglob("*.py")
            if "__pycache__" not in ruta.parts
        )

    return sorted(
        scripts,
        key=lambda ruta: str(
            ruta.relative_to(ROOT)
        ).lower(),
    )


def leer_texto(
    ruta,
):

    return ruta.read_text(
        encoding="utf-8-sig"
    )


def obtener_docstring(
    texto,
):

    try:

        arbol = ast.parse(
            texto
        )

    except SyntaxError as error:

        return None, (
            "ERROR_SINTAXIS",
            (
                f"Línea {error.lineno}: "
                f"{error.msg}"
            ),
        )

    docstring = ast.get_docstring(
        arbol,
        clean=False,
    )

    return docstring, None


def archivo_init_vacio(
    ruta,
    texto,
):

    if ruta.name != "__init__.py":
        return False

    contenido = texto.strip()

    if not contenido:
        return True

    try:

        arbol = ast.parse(
            texto
        )

    except SyntaxError:

        return False

    return (
        not arbol.body
        or all(
            isinstance(
                nodo,
                ast.Expr,
            )
            and isinstance(
                nodo.value,
                ast.Constant,
            )
            and isinstance(
                nodo.value.value,
                str,
            )
            for nodo in arbol.body
        )
    )


def contiene_campo(
    docstring,
    campo,
):

    patron = re.compile(
        rf"(?mi)^\s*{re.escape(campo)}\s*:",
    )

    return bool(
        patron.search(
            docstring
        )
    )


def extraer_valor_linea(
    docstring,
    campo,
):

    patron = re.compile(
        rf"(?mi)^\s*{re.escape(campo)}\s*:\s*(.*?)\s*$"
    )

    coincidencia = patron.search(
        docstring
    )

    if coincidencia is None:
        return None

    return coincidencia.group(1).strip()


def auditar_script(
    ruta,
):

    relativa = str(
        ruta.relative_to(
            ROOT
        )
    ).replace(
        "\\",
        "/",
    )

    texto = leer_texto(
        ruta
    )

    if archivo_init_vacio(
        ruta,
        texto,
    ):

        return {
            "ruta": relativa,
            "estado": "CORRECTA",
            "incidencias": [],
        }

    docstring, error = obtener_docstring(
        texto
    )

    if error is not None:

        tipo_error, detalle = error

        return {
            "ruta": relativa,
            "estado": tipo_error,
            "incidencias": [
                detalle
            ],
        }

    if not docstring:

        return {
            "ruta": relativa,
            "estado": "SIN_CABECERA",
            "incidencias": [
                "El archivo no contiene docstring inicial."
            ],
        }

    incidencias = []

    for campo in CAMPOS_OBLIGATORIOS:

        if not contiene_campo(
            docstring,
            campo,
        ):

            incidencias.append(
                f"Falta el campo: {campo}."
            )

    proyecto = extraer_valor_linea(
        docstring,
        "Proyecto",
    )

    if (
        proyecto is not None
        and proyecto != "OpoCoach"
    ):

        incidencias.append(
            "Proyecto debe ser OpoCoach."
        )

    tipo = extraer_valor_linea(
        docstring,
        "Tipo",
    )

    if (
        tipo is not None
        and tipo not in TIPOS_VALIDOS
    ):

        incidencias.append(
            "Tipo no válido: "
            f"{tipo!r}."
        )

    estado = extraer_valor_linea(
        docstring,
        "Estado",
    )

    if (
        estado is not None
        and estado not in ESTADOS_VALIDOS
    ):

        incidencias.append(
            "Estado no válido: "
            f"{estado!r}."
        )

    archivo = extraer_valor_linea(
        docstring,
        "Archivo",
    )

    if (
        archivo is not None
        and archivo != ruta.name
    ):

        incidencias.append(
            "El campo Archivo no coincide "
            f"con {ruta.name!r}."
        )

    ruta_cabecera = extraer_valor_linea(
        docstring,
        "Ruta",
    )

    if ruta_cabecera is not None:

        ruta_normalizada = ruta_cabecera.replace(
            "\\",
            "/",
        )

        if ruta_normalizada != relativa:

            incidencias.append(
                "El campo Ruta no coincide "
                f"con {relativa!r}."
            )

    return {
        "ruta": relativa,
        "estado": (
            "CORRECTA"
            if not incidencias
            else "INCOMPLETA"
        ),
        "incidencias": incidencias,
    }


def generar_informe(
    resultados,
):

    RUTA_INFORME.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    correctas = [
        resultado
        for resultado in resultados
        if resultado["estado"] == "CORRECTA"
    ]

    incompletas = [
        resultado
        for resultado in resultados
        if resultado["estado"] == "INCOMPLETA"
    ]

    sin_cabecera = [
        resultado
        for resultado in resultados
        if resultado["estado"] == "SIN_CABECERA"
    ]

    errores = [
        resultado
        for resultado in resultados
        if resultado["estado"] == "ERROR_SINTAXIS"
    ]

    lineas = [
        "# OpoCoach",
        "",
        "**Documento:** Auditoría de cabeceras",
        "",
        "## Resumen",
        "",
        "| Estado | Cantidad |",
        "|---|---:|",
        f"| Correctas | {len(correctas)} |",
        f"| Incompletas | {len(incompletas)} |",
        f"| Sin cabecera | {len(sin_cabecera)} |",
        f"| Error de sintaxis | {len(errores)} |",
        f"| Total | {len(resultados)} |",
        "",
    ]

    if incompletas:

        lineas.extend(
            [
                "## Cabeceras incompletas",
                "",
            ]
        )

        for resultado in incompletas:

            lineas.append(
                f"### `{resultado['ruta']}`"
            )

            lineas.append("")

            for incidencia in resultado[
                "incidencias"
            ]:

                lineas.append(
                    f"- {incidencia}"
                )

            lineas.append("")

    if sin_cabecera:

        lineas.extend(
            [
                "## Archivos sin cabecera",
                "",
            ]
        )

        for resultado in sin_cabecera:

            lineas.append(
                f"- `{resultado['ruta']}`"
            )

        lineas.append("")

    if errores:

        lineas.extend(
            [
                "## Errores de sintaxis",
                "",
            ]
        )

        for resultado in errores:

            lineas.append(
                f"### `{resultado['ruta']}`"
            )

            lineas.append("")

            for incidencia in resultado[
                "incidencias"
            ]:

                lineas.append(
                    f"- {incidencia}"
                )

            lineas.append("")

    if correctas:

        lineas.extend(
            [
                "## Cabeceras correctas",
                "",
            ]
        )

        for resultado in correctas:

            lineas.append(
                f"- `{resultado['ruta']}`"
            )

        lineas.append("")

    RUTA_INFORME.write_text(
        "\n".join(
            lineas
        ),
        encoding="utf-8",
    )


def main():

    scripts = obtener_scripts()

    resultados = [
        auditar_script(
            ruta
        )
        for ruta in scripts
    ]

    generar_informe(
        resultados
    )

    resumen = {
        "CORRECTA": 0,
        "INCOMPLETA": 0,
        "SIN_CABECERA": 0,
        "ERROR_SINTAXIS": 0,
    }

    for resultado in resultados:

        resumen[
            resultado["estado"]
        ] += 1

    print()
    print("=" * 70)
    print("AUDITORÍA DE CABECERAS")
    print("=" * 70)

    print(
        f"Scripts...........: {len(resultados)}"
    )

    print(
        f"Correctas.........: {resumen['CORRECTA']}"
    )

    print(
        f"Incompletas.......: {resumen['INCOMPLETA']}"
    )

    print(
        f"Sin cabecera......: {resumen['SIN_CABECERA']}"
    )

    print(
        f"Errores sintaxis..: {resumen['ERROR_SINTAXIS']}"
    )

    print(
        f"Informe...........: {RUTA_INFORME}"
    )


if __name__ == "__main__":

    main()