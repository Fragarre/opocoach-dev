"""
Archivo: test_buscar_fragmentos.py
Ruta: tests/test_buscar_fragmentos.py

Dependencias:
- sqlite3
- pathlib
- core.buscar_fragmentos
- core.temario

Funcionalidad:
Valida que BM25 busque únicamente entre los documentos definidos
en el temario de la convocatoria.

Comprueba:
- búsqueda limitada a una norma;
- búsqueda global;
- ausencia de documentos ajenos al CFG.
"""

import sqlite3
from pathlib import Path

from core.buscar_fragmentos import buscar_fragmentos
from core.temario import Temario


DB_PATH = Path("db/oposiciones.sqlite3")

CONSULTA = """
Recurso de alzada contra una resolución administrativa.
Plazo para interponer el recurso y plazo máximo para resolver.
"""

LIMITE = 5


def mostrar_resultados(titulo, resultados):

    print()
    print("=" * 80)
    print(titulo)
    print("=" * 80)
    print(f"Resultados: {len(resultados)}")

    for posicion, resultado in enumerate(
        resultados,
        start=1,
    ):

        print()
        print(
            f"{posicion}. "
            f"Fragmento {resultado['fragmento_id']} | "
            f"Score {resultado['score']:.4f}"
        )
        print(
            f"Documento: {resultado['nombre_archivo']}"
        )
        print(
            f"Referencia: {resultado['referencia']}"
        )


def validar_documentos_permitidos(
    resultados,
    documentos_permitidos,
    descripcion,
):

    documentos_permitidos = set(
        documentos_permitidos
    )

    incorrectos = [
        resultado["nombre_archivo"]
        for resultado in resultados
        if resultado["nombre_archivo"]
        not in documentos_permitidos
    ]

    if incorrectos:

        raise AssertionError(
            f"{descripcion}: BM25 devolvió documentos "
            f"fuera del temario: {incorrectos}"
        )


def main():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: "
            f"{DB_PATH.resolve()}"
        )

    temario = Temario()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    try:

        # --------------------------------------------------
        # PRUEBA 1
        # Búsqueda limitada a la Ley 39/2015
        # --------------------------------------------------

        documentos_l39 = (
            temario.obtener_documentos_norma(
                "L39_2015"
            )
        )

        resultados_norma = buscar_fragmentos(
            conn=conn,
            temario=temario,
            texto_consulta=CONSULTA,
            codigo_norma="L39_2015",
            limite=LIMITE,
        )

        if not resultados_norma:
            raise AssertionError(
                "La búsqueda limitada a L39_2015 "
                "no devolvió resultados."
            )

        validar_documentos_permitidos(
            resultados=resultados_norma,
            documentos_permitidos=documentos_l39,
            descripcion="Búsqueda L39_2015",
        )

        mostrar_resultados(
            titulo="PRUEBA 1 — BÚSQUEDA LIMITADA A L39_2015",
            resultados=resultados_norma,
        )

        # --------------------------------------------------
        # PRUEBA 2
        # Búsqueda global en todo el temario
        # --------------------------------------------------

        documentos_temario = (
            temario.obtener_documentos()
        )

        resultados_globales = buscar_fragmentos(
            conn=conn,
            temario=temario,
            texto_consulta=CONSULTA,
            codigo_norma=None,
            limite=LIMITE,
        )

        if not resultados_globales:
            raise AssertionError(
                "La búsqueda global no devolvió resultados."
            )

        validar_documentos_permitidos(
            resultados=resultados_globales,
            documentos_permitidos=documentos_temario,
            descripcion="Búsqueda global",
        )

        mostrar_resultados(
            titulo="PRUEBA 2 — BÚSQUEDA GLOBAL",
            resultados=resultados_globales,
        )

        # --------------------------------------------------
        # PRUEBA 3
        # Norma fuera del temario
        # --------------------------------------------------

        resultados_fuera = buscar_fragmentos(
            conn=conn,
            temario=temario,
            texto_consulta=CONSULTA,
            codigo_norma="L22_2009",
            limite=LIMITE,
        )

        if resultados_fuera:
            raise AssertionError(
                "Una norma fuera del temario devolvió "
                "fragmentos."
            )

        print()
        print("=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)
        print("Búsqueda por norma........: OK")
        print("Búsqueda global...........: OK")
        print("Filtro por CFG............: OK")
        print("Norma fuera del temario...: OK")

    finally:
        conn.close()


if __name__ == "__main__":
    main()