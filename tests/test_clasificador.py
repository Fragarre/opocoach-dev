"""
Archivo: test_clasificador.py
Ruta: tests/test_clasificador.py

Dependencias:
- core.temario
- core.clasificador

Funcionalidad:
Valida el funcionamiento de la clasificación determinista del Proceso 3.

Ejecuta un conjunto de casos controlados que verifican:

- detección de norma y artículo;
- rechazo de normas fuera del temario;
- rechazo de artículos fuera del temario;
- clasificación de artículos pertenecientes al temario;
- detección de referencias ambiguas;
- casos pendientes que deberán continuar mediante BM25 e IA.

No modifica la base de datos.
"""


from core.temario import Temario
from core.clasificador import Clasificador


CASOS = [

    (
        "Artículo válido",
        "Según el artículo 52 de la Ley 39/2015...",
        "VALIDADA",
    ),

    (
        "Artículo fuera del temario",
        "Según el artículo 200 de la Ley 39/2015...",
        "RECHAZADA",
    ),

    (
        "Norma fuera del temario",
        "Según la Ley 7/1985...",
        "RECHAZADA",
    ),

    (
        "Norma sin artículo",
        "Según la Ley 39/2015...",
        "PENDIENTE",
    ),

    (
        "Sin norma",
        "¿Cuál de las siguientes afirmaciones es correcta?",
        "PENDIENTE",
    ),

    (
        "Artículo compartido",
        "Según el artículo 30 de la Ley 1/2015...",
        "A_REVISAR",
    ),

    (
        "Varias normas",
        (
            "Según la Constitución Española y la "
            "Ley 39/2015, señale la respuesta correcta."
        ),
        "RECHAZADA",
    ),
    
]


def main():

    temario = Temario()

    clasificador = Clasificador(
        temario
    )

    print()
    print("=" * 80)
    print("PRUEBA CLASIFICADOR DIRECTO")
    print("=" * 80)

    errores = 0

    for descripcion, texto, esperado in CASOS:

        resultado = clasificador.clasificar_directa(
            texto
        )

        obtenido = resultado["estado"]

        correcto = obtenido == esperado

        print()
        print(descripcion)
        print("-" * 80)
        print(texto)
        print(f"Esperado : {esperado}")
        print(f"Obtenido : {obtenido}")

        if correcto:
            print("OK")
        else:
            print("ERROR")
            errores += 1

    print()
    print("=" * 80)

    if errores:
        print(f"ERRORES: {errores}")
    else:
        print("TODAS LAS PRUEBAS SUPERADAS")


if __name__ == "__main__":
    main()