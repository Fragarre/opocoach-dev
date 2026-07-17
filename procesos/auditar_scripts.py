"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : auditar_scripts.py
Ruta    : procesos/auditar_scripts.py

Objetivo:
    Analizar dependencias y detectar scripts activos, manuales u obsoletos.

Entradas:
    - Scripts Python del proyecto.

Salidas:
    - docs/AUDITORIA_SCRIPTS.md.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - Ninguna.

Flujo:
    1. Analiza imports.
    2. Relaciona dependencias.
    3. Clasifica scripts.
    4. Genera informe.

Observaciones:
    - Ninguna.

==============================================================================
"""
import ast
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CARPETAS_CODIGO = (
    ROOT / "core",
    ROOT / "procesos",
    ROOT / "render",
)

RUTA_INFORME = (
    ROOT
    / "docs"
    / "AUDITORIA_SCRIPTS.md"
)


def ruta_relativa(
    ruta,
):

    return str(
        ruta.relative_to(
            ROOT
        )
    ).replace(
        "\\",
        "/",
    )


def modulo_desde_ruta(
    ruta,
):

    relativa = ruta.relative_to(
        ROOT
    )

    partes = list(
        relativa.with_suffix(
            ""
        ).parts
    )

    if partes[-1] == "__init__":

        partes = partes[:-1]

    return ".".join(
        partes
    )


def obtener_scripts():

    scripts = []

    for carpeta in CARPETAS_CODIGO:

        if not carpeta.exists():
            continue

        for ruta in carpeta.rglob(
            "*.py"
        ):

            if "__pycache__" in ruta.parts:
                continue

            scripts.append(
                ruta
            )

    return sorted(
        scripts,
        key=lambda ruta: ruta_relativa(
            ruta
        ).lower(),
    )


def analizar_script(
    ruta,
):

    texto = ruta.read_text(
        encoding="utf-8-sig"
    )

    arbol = ast.parse(
        texto
    )

    imports = set()

    funciones = []

    clases = []

    tiene_main = False

    for nodo in ast.walk(
        arbol
    ):

        if isinstance(
            nodo,
            ast.Import,
        ):

            for alias in nodo.names:

                nombre = alias.name

                if nombre.startswith(
                    (
                        "core",
                        "procesos",
                        "render",
                    )
                ):

                    imports.add(
                        nombre
                    )

        elif isinstance(
            nodo,
            ast.ImportFrom,
        ):

            if nodo.module is None:
                continue

            if nodo.module.startswith(
                (
                    "core",
                    "procesos",
                    "render",
                )
            ):

                imports.add(
                    nodo.module
                )

        elif isinstance(
            nodo,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            funciones.append(
                nodo.name
            )

        elif isinstance(
            nodo,
            ast.ClassDef,
        ):

            clases.append(
                nodo.name
            )

        elif isinstance(
            nodo,
            ast.If,
        ):

            prueba = nodo.test

            if not isinstance(
                prueba,
                ast.Compare,
            ):

                continue

            if len(
                prueba.ops
            ) != 1:

                continue

            if not isinstance(
                prueba.ops[0],
                ast.Eq,
            ):

                continue

            valores = [
                prueba.left,
                *prueba.comparators,
            ]

            textos = []

            for valor in valores:

                if isinstance(
                    valor,
                    ast.Name,
                ):

                    textos.append(
                        valor.id
                    )

                elif isinstance(
                    valor,
                    ast.Constant,
                ):

                    textos.append(
                        valor.value
                    )

            if (
                "__name__" in textos
                and "__main__" in textos
            ):

                tiene_main = True

    return {
        "ruta": ruta_relativa(
            ruta
        ),
        "modulo": modulo_desde_ruta(
            ruta
        ),
        "imports": sorted(
            imports
        ),
        "funciones": sorted(
            set(
                funciones
            )
        ),
        "clases": sorted(
            set(
                clases
            )
        ),
        "tiene_main": tiene_main,
    }


def relacionar_dependencias(
    resultados,
):

    modulos = {
        resultado["modulo"]: resultado
        for resultado in resultados
        if resultado["modulo"]
    }

    utilizados_por = defaultdict(
        set
    )

    for resultado in resultados:

        for importado in resultado[
            "imports"
        ]:

            candidatos = [
                modulo
                for modulo in modulos
                if (
                    importado == modulo
                    or importado.startswith(
                        modulo + "."
                    )
                    or modulo.startswith(
                        importado + "."
                    )
                )
            ]

            for candidato in candidatos:

                if (
                    candidato
                    != resultado["modulo"]
                ):

                    utilizados_por[
                        candidato
                    ].add(
                        resultado["ruta"]
                    )

    for resultado in resultados:

        resultado[
            "utilizado_por"
        ] = sorted(
            utilizados_por[
                resultado["modulo"]
            ]
        )

    return resultados


def clasificar(
    resultado,
):

    ruta = resultado[
        "ruta"
    ]

    if ruta.endswith(
        "__init__.py"
    ):

        return (
            "INFRAESTRUCTURA",
            "Archivo de paquete Python.",
        )

    if resultado[
        "utilizado_por"
    ]:

        return (
            "ACTIVO",
            "Es utilizado por otros scripts.",
        )

    if (
        ruta.startswith(
            "procesos/"
        )
        and resultado[
            "tiene_main"
        ]
    ):

        return (
            "PROCESO_MANUAL",
            (
                "Proceso ejecutable no importado "
                "por otros módulos."
            ),
        )

    if (
        ruta.startswith(
            "core/"
        )
        and not resultado[
            "utilizado_por"
        ]
    ):

        return (
            "REVISAR",
            (
                "Módulo core no utilizado por "
                "ningún script analizado."
            ),
        )

    if (
        ruta.startswith(
            "render/"
        )
        and not resultado[
            "utilizado_por"
        ]
    ):

        return (
            "REVISAR",
            (
                "Módulo de render no utilizado por "
                "ningún script analizado."
            ),
        )

    return (
        "REVISAR",
        "No se ha detectado uso interno.",
    )


def generar_informe(
    resultados,
):

    RUTA_INFORME.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grupos = defaultdict(
        list
    )

    for resultado in resultados:

        estado, motivo = clasificar(
            resultado
        )

        resultado[
            "estado_auditoria"
        ] = estado

        resultado[
            "motivo_auditoria"
        ] = motivo

        grupos[
            estado
        ].append(
            resultado
        )

    orden = (
        "REVISAR",
        "PROCESO_MANUAL",
        "ACTIVO",
        "INFRAESTRUCTURA",
    )

    lineas = [
        "# OpoCoach",
        "",
        "**Documento:** Auditoría de scripts",
        "",
        "## Resumen",
        "",
        "| Estado | Cantidad |",
        "|---|---:|",
    ]

    for estado in orden:

        lineas.append(
            f"| {estado} | "
            f"{len(grupos[estado])} |"
        )

    lineas.extend(
        [
            f"| Total | {len(resultados)} |",
            "",
        ]
    )

    for estado in orden:

        lineas.extend(
            [
                f"## {estado}",
                "",
            ]
        )

        if not grupos[
            estado
        ]:

            lineas.extend(
                [
                    "Ninguno.",
                    "",
                ]
            )

            continue

        for resultado in grupos[
            estado
        ]:

            lineas.append(
                f"### `{resultado['ruta']}`"
            )

            lineas.append("")

            lineas.append(
                resultado[
                    "motivo_auditoria"
                ]
            )

            lineas.append("")

            lineas.append(
                f"- Módulo: "
                f"`{resultado['modulo']}`"
            )

            lineas.append(
                f"- Ejecutable: "
                f"{'Sí' if resultado['tiene_main'] else 'No'}"
            )

            if resultado[
                "utilizado_por"
            ]:

                lineas.append(
                    "- Utilizado por:"
                )

                for usuario in resultado[
                    "utilizado_por"
                ]:

                    lineas.append(
                        f"  - `{usuario}`"
                    )

            else:

                lineas.append(
                    "- Utilizado por: ninguno detectado."
                )

            if resultado[
                "imports"
            ]:

                lineas.append(
                    "- Utiliza:"
                )

                for modulo in resultado[
                    "imports"
                ]:

                    lineas.append(
                        f"  - `{modulo}`"
                    )

            else:

                lineas.append(
                    "- Utiliza módulos internos: no."
                )

            if resultado[
                "funciones"
            ]:

                lineas.append(
                    "- Funciones:"
                )

                for funcion in resultado[
                    "funciones"
                ]:

                    lineas.append(
                        f"  - `{funcion}()`"
                    )

            if resultado[
                "clases"
            ]:

                lineas.append(
                    "- Clases:"
                )

                for clase in resultado[
                    "clases"
                ]:

                    lineas.append(
                        f"  - `{clase}`"
                    )

            lineas.append("")

    RUTA_INFORME.write_text(
        "\n".join(
            lineas
        ),
        encoding="utf-8",
    )

    return grupos


def main():

    resultados = []

    for ruta in obtener_scripts():

        try:

            resultados.append(
                analizar_script(
                    ruta
                )
            )

        except SyntaxError as error:

            print(
                f"ERROR DE SINTAXIS "
                f"{ruta_relativa(ruta)}: "
                f"{error}"
            )

    resultados = relacionar_dependencias(
        resultados
    )

    grupos = generar_informe(
        resultados
    )

    print()
    print("=" * 70)
    print("AUDITORÍA DE SCRIPTS")
    print("=" * 70)

    print(
        f"Scripts...........: {len(resultados)}"
    )

    print(
        f"Activos...........: "
        f"{len(grupos['ACTIVO'])}"
    )

    print(
        f"Procesos manuales.: "
        f"{len(grupos['PROCESO_MANUAL'])}"
    )

    print(
        f"A revisar.........: "
        f"{len(grupos['REVISAR'])}"
    )

    print(
        f"Infraestructura...: "
        f"{len(grupos['INFRAESTRUCTURA'])}"
    )

    print(
        f"Informe...........: {RUTA_INFORME}"
    )


if __name__ == "__main__":

    main()