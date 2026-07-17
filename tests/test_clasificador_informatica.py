"""
Archivo: test_clasificador_informatica.py
Ruta: tests/test_clasificador_informatica.py

Dependencias:
- sqlite3
- pathlib
- core.temario
- core.buscar_fragmentos

Funcionalidad:
Comprueba la recuperación documental de una pregunta de Informática.

La prueba valida que BM25:

- busca únicamente dentro de los documentos incluidos en el temario;
- localiza fragmentos conceptualmente relacionados con la pregunta;
- devuelve el documento de Informática correspondiente;
- permite obtener el tema mediante Temario.

Esta prueba no llama a la API de OpenAI.

No modifica la base de datos.
"""

import sqlite3
from pathlib import Path

from core.buscar_fragmentos import buscar_fragmentos
from core.temario import Temario


RUTA_BD = Path(
    "db/oposiciones.sqlite3"
)


PREGUNTA = (
    "En Microsoft Excel, ¿qué función permite "
    "sumar los valores de un rango de celdas?"
)


OPCIONES = {
    "A": "La función SUMA.",
    "B": "La función CONTAR.",
    "C": "La función PROMEDIO.",
    "D": "La función SI.",
}


RESPUESTA_CORRECTA = "A"


def abrir_conexion():

    if not RUTA_BD.exists():

        raise FileNotFoundError(
            "No existe la base de datos: "
            f"{RUTA_BD.resolve()}"
        )

    return sqlite3.connect(
        RUTA_BD
    )


def main():

    temario = Temario()
    conn = abrir_conexion()

    try:

        texto_consulta = (
            PREGUNTA
            + "\n"
            + OPCIONES[
                RESPUESTA_CORRECTA
            ]
        )

        fragmentos = buscar_fragmentos(
            conn=conn,
            temario=temario,
            texto_consulta=texto_consulta,
            codigo_norma=None,
            limite=10,
        )

        print()
        print("=" * 80)
        print(
            "PRUEBA DE RECUPERACIÓN — INFORMÁTICA"
        )
        print("=" * 80)
        print(
            f"Pregunta: {PREGUNTA}"
        )
        print(
            f"Respuesta: "
            f"{OPCIONES[RESPUESTA_CORRECTA]}"
        )
        print()
        print(
            f"Fragmentos encontrados: "
            f"{len(fragmentos)}"
        )

        if not fragmentos:

            print()
            print(
                "RESULTADO: ERROR"
            )
            print(
                "BM25 no ha recuperado ningún "
                "fragmento."
            )
            return

        encontrado_informatica = False

        for posicion, fragmento in enumerate(
            fragmentos,
            start=1,
        ):

            asociaciones = (
                temario.obtener_asociaciones_documento(
                    fragmento["nombre_archivo"]
                )
            )

            print()
            print("-" * 80)
            print(
                f"Resultado {posicion}"
            )
            print(
                f"Fragmento..........: "
                f"{fragmento['fragmento_id']}"
            )
            print(
                f"Score..............: "
                f"{fragmento['score']:.4f}"
            )
            print(
                f"Documento..........: "
                f"{fragmento['nombre_archivo']}"
            )
            print(
                f"Referencia.........: "
                f"{fragmento['referencia']}"
            )

            for asociacion in asociaciones:

                es_informatica = (
                    temario.es_informatica(
                        asociacion["parte"],
                        asociacion["tema"],
                    )
                )

                print(
                    f"Parte..............: "
                    f"{asociacion['parte']}"
                )
                print(
                    f"Tema...............: "
                    f"{asociacion['tema']}"
                )
                print(
                    f"Es Informática.....: "
                    f"{es_informatica}"
                )

                if es_informatica:
                    encontrado_informatica = True

        print()
        print("=" * 80)

        if encontrado_informatica:

            print(
                "RESULTADO: BM25 HA LOCALIZADO "
                "DOCUMENTACIÓN DE INFORMÁTICA"
            )

        else:

            print(
                "RESULTADO: ERROR — LOS CANDIDATOS "
                "NO PERTENECEN A INFORMÁTICA"
            )

        print("=" * 80)

    finally:

        conn.close()


if __name__ == "__main__":
    main()