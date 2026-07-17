"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : constructor_simulacro.py
Ruta    : core/constructor_simulacro.py

Objetivo:
    Construir un simulacro con la distribución oficial de la convocatoria.

Entradas:
    - Distribución del modelo.
    - Banco de preguntas.

Salidas:
    - Simulacro estructurado y relación de faltantes.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.distribucion_modelo
    - core.selector_banco

Utilizado por:
    - procesos/generar_simulacro.py

Flujo:
    1. Carga la distribución.
    2. Selecciona preguntas por tipo y tema.
    3. Evita repeticiones.
    4. Completa faltantes cuando es posible.

Observaciones:
    - Ninguna.

==============================================================================
"""
import random

from core.distribucion_modelo import (
    obtener_distribucion_modelo,
)

from core.selector_banco import (
    seleccionar_preguntas,
)


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


def añadir_preguntas(
    destino,
    preguntas,
    usadas,
):

    for pregunta in preguntas:

        pregunta_id = pregunta["id"]

        if pregunta_id in usadas:
            continue

        usadas.add(
            pregunta_id
        )

        destino.append(
            pregunta
        )


def completar_desde_otros_temas(
    bloque,
    cantidad,
    temas_disponibles,
    usadas,
    codigo_cfg,
):

    preguntas_extra = []

    temas = list(
        temas_disponibles
    )

    random.shuffle(
        temas
    )

    while cantidad > 0:

        encontrada = False

        for tema in temas:

            resultado = seleccionar_preguntas(
                tipo_pregunta=bloque,
                tema=tema,
                cantidad=1,
                excluidas=usadas,
                codigo_cfg=codigo_cfg,
            )

            if not resultado["preguntas"]:
                continue

            pregunta = resultado[
                "preguntas"
            ][0]

            usadas.add(
                pregunta["id"]
            )

            preguntas_extra.append(
                pregunta
            )

            cantidad -= 1
            encontrada = True

            if cantidad == 0:
                break

        if not encontrada:
            break

    return preguntas_extra


def construir_simulacro(
    codigo_cfg,
):

    distribucion = (
        obtener_distribucion_modelo()
    )

    usadas = set()

    simulacro = []

    resumen_bloques = {}

    compensaciones = []

    faltantes_por_tema = []

    for bloque in ORDEN_BLOQUES:

        preguntas_bloque = []

        faltantes_bloque = []

        temas_bloque = sorted(
            distribucion.get(
                bloque,
                {},
            )
        )

        for tema, cantidad in sorted(
            distribucion.get(
                bloque,
                {},
            ).items()
        ):

            resultado = seleccionar_preguntas(
                tipo_pregunta=bloque,
                tema=tema,
                cantidad=cantidad,
                excluidas=usadas,
            )

            añadir_preguntas(
                destino=preguntas_bloque,
                preguntas=resultado[
                    "preguntas"
                ],
                usadas=usadas,
            )

            if resultado["faltan"] > 0:

                faltantes_bloque.append({
                    "tema": tema,
                    "cantidad": resultado[
                        "faltan"
                    ],
                })

                faltantes_por_tema.append({
                    "tipo_pregunta": bloque,
                    "tema": tema,
                    "faltan": resultado[
                        "faltan"
                    ],
                })

        if bloque != "ESPECIAL_INFORMATICA":

            total_faltante = sum(
                dato["cantidad"]
                for dato in faltantes_bloque
            )

            if total_faltante > 0:

                extras = (
                    completar_desde_otros_temas(
                        bloque=bloque,
                        cantidad=total_faltante,
                        temas_disponibles=(
                            temas_bloque
                        ),
                        usadas=usadas,
                        codigo_cfg=codigo_cfg,
                    )
                )

                preguntas_bloque.extend(
                    extras
                )

                if extras:

                    compensaciones.append({
                        "tipo_pregunta": bloque,
                        "cantidad": len(
                            extras
                        ),
                    })

        random.shuffle(
            preguntas_bloque
        )

        simulacro.extend(
            preguntas_bloque
        )

        resumen_bloques[
            bloque
        ] = {
            "objetivo": TOTALES_OFICIALES[
                bloque
            ],
            "obtenidas": len(
                preguntas_bloque
            ),
            "faltan": max(
                0,
                TOTALES_OFICIALES[bloque]
                - len(preguntas_bloque),
            ),
        }

    for numero, pregunta in enumerate(
        simulacro,
        start=1,
    ):

        pregunta[
            "numero_simulacro"
        ] = numero

    faltantes_reales = []

    for bloque in ORDEN_BLOQUES:

        faltan = resumen_bloques[
            bloque
        ]["faltan"]

        if faltan > 0:

            faltantes_reales.append({
                "tipo_pregunta": bloque,
                "faltan": faltan,
            })

    return {
        "simulacro": simulacro,
        "total": len(simulacro),
        "completo": (
            len(simulacro) == 110
            and not faltantes_reales
        ),
        "faltantes": faltantes_reales,
        "faltantes_por_tema": (
            faltantes_por_tema
        ),
        "compensaciones": compensaciones,
        "resumen_bloques": resumen_bloques,
    }


def prueba():

    resultado = construir_simulacro(
    codigo_cfg="C1-01_58_26",
    )

    print()
    print("=" * 80)
    print("CONSTRUCTOR DE SIMULACRO")
    print("=" * 80)

    for bloque in ORDEN_BLOQUES:

        datos = resultado[
            "resumen_bloques"
        ][bloque]

        print(
            f"{bloque:<24}: "
            f"{datos['obtenidas']} / "
            f"{datos['objetivo']}"
        )

    print("-" * 80)

    print(
        f"Preguntas obtenidas: "
        f"{resultado['total']}"
    )


    print(
        f"Completo...........: "
        f"{resultado['completo']}"
    )

    if resultado["compensaciones"]:

        print()
        print("COMPENSACIONES")

        for dato in resultado[
            "compensaciones"
        ]:

            print(
                f"{dato['tipo_pregunta']:<24} "
                f"{dato['cantidad']}"
            )

    if resultado["faltantes"]:

        print()
        print("FALTANTES")

        for dato in resultado[
            "faltantes"
        ]:

            print(
                f"{dato['tipo_pregunta']:<24} "
                f"{dato['faltan']}"
            )


if __name__ == "__main__":

    prueba()