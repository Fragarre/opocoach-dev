"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

------------------------------------------------------------------------------
Archivo : verificar_proyecto.py
Ruta    : procesos/verificar_proyecto.py
------------------------------------------------------------------------------

Objetivo:
    Verificar que el proyecto está correctamente instalado y preparado para
    trabajar con una convocatoria.

Entradas:
    - Proyecto OpoCoach.

Salidas:
    - Informe de verificación.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - pathlib
    - sqlite3
    - importlib

Utilizado por:
    - Ejecución manual.

Flujo:
    1. Comprueba la base de datos.
    2. Comprueba documentación.
    3. Comprueba directorios.
    4. Comprueba dependencias.
    5. Muestra un resumen.

Observaciones:
    - No modifica ningún dato del proyecto.

==============================================================================
"""

from pathlib import Path
import sqlite3
import importlib
import sys


ROOT = Path(__file__).resolve().parents[1]

BASE_DATOS = ROOT / "db" / "oposiciones.sqlite3"

DIRECTORIOS = [
    "config",
    "core",
    "procesos",
    "docs",
    "db",
    "logs",
]

DOCUMENTOS = [
    "00_FUNCIONALIDAD.md",
    "01_ESTRUCTURA_PROYECTO.md",
    "02_CONVENCIONES.md",
    "03_ARQUITECTURA_BD.md",
    "04_SCRIPTS.md",
    "05_ESTADO.md",
    "06_HISTORIAL_VERSIONES.md",
]

TABLAS = [
    "convocatorias",
    "temas",
    "documentos",
    "documentos_temas",
    "fragmentos",
    "indice_fragmentos",
    "preguntas",
    "opciones",
]

LIBRERIAS = [
    "sqlite3",
    "json",
    "openai",
]

errores = 0
avisos = 0


def ok(valor):

    return "OK" if valor else "ERROR"


def aviso(valor):

    return "OK" if valor else "AVISO"


def imprimir(nombre, estado):

    print(f"{nombre:.<40}{estado}")


def comprobar_bd():

    if not BASE_DATOS.exists():
        return False

    try:

        conn = sqlite3.connect(BASE_DATOS)

        cur = conn.cursor()

        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        )

        tablas = {
            fila[0]
            for fila in cur.fetchall()
        }

        conn.close()

    except Exception:

        return False

    return all(
        tabla in tablas
        for tabla in TABLAS
    )


def comprobar_directorios():

    return all(
        (ROOT / directorio).exists()
        for directorio in DIRECTORIOS
    )


def comprobar_documentacion():

    carpeta = ROOT / "docs"

    if not carpeta.exists():
        return False

    for documento in DOCUMENTOS:

        if not (carpeta / documento).exists():
            return False

    return True


def comprobar_dependencias():

    for libreria in LIBRERIAS:

        try:

            importlib.import_module(
                libreria
            )

        except Exception:

            return False

    return True

def comprobar_cabeceras():

    fichero = (
        ROOT
        / "docs"
        / "CABECERAS_PENDIENTES.md"
    )

    if not fichero.exists():
        return False

    texto = fichero.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    return (
        "| Incompletas | 0 |" in texto
        and
        "| Sin cabecera | 0 |" in texto
        and
        "| Error de sintaxis | 0 |" in texto
    )


def comprobar_indice():

    try:

        conn = sqlite3.connect(
            BASE_DATOS
        )

        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM indice_fragmentos
            """
        )

        total = cur.fetchone()[0]

        conn.close()

        return total > 0

    except Exception:

        return False


def comprobar_openai():

    try:

        import openai

        return True

    except Exception:

        return False


def comprobar_cfg():

    carpeta = ROOT / "config"

    if not carpeta.exists():
        return False

    cfg = list(
        carpeta.glob("*.cfg")
    )

    return len(cfg) > 0


def comprobar_documentos():

    carpeta = ROOT / "data"

    if not carpeta.exists():
        return False

    pdf = list(
        carpeta.rglob("*.pdf")
    )

    return len(pdf) > 0


def verificar(
    nombre,
    funcion,
    obligatorio=True,
):

    global errores
    global avisos

    try:

        resultado = funcion()

    except Exception:

        resultado = False

    if obligatorio:

        estado = ok(
            resultado
        )

        if not resultado:
            errores += 1

    else:

        estado = aviso(
            resultado
        )

        if not resultado:
            avisos += 1

    imprimir(
        nombre,
        estado,
    )

    return resultado

def main():

    print()
    print("=" * 70)
    print("VERIFICACIÓN DEL PROYECTO")
    print("=" * 70)
    print()

    verificar(
        "Base de datos",
        comprobar_bd,
    )

    verificar(
        "Directorios",
        comprobar_directorios,
    )

    verificar(
        "Documentación",
        comprobar_documentacion,
    )

    verificar(
        "Cabeceras",
        comprobar_cabeceras,
    )

    verificar(
        "Índice de fragmentos",
        comprobar_indice,
    )

    verificar(
        "Configuración (CFG)",
        comprobar_cfg,
        obligatorio=False,
    )

    verificar(
        "Documentos PDF",
        comprobar_documentos,
        obligatorio=False,
    )

    verificar(
        "OpenAI",
        comprobar_openai,
        obligatorio=False,
    )

    verificar(
        "Dependencias",
        comprobar_dependencias,
    )

    print()
    print("-" * 70)

    print(
        f"ERRORES........................ {errores}"
    )

    print(
        f"AVISOS......................... {avisos}"
    )

    print()

    if errores == 0:

        print(
            "PROYECTO OPERATIVO"
        )

    else:

        print(
            "PROYECTO NO OPERATIVO"
        )

    print("=" * 70)

    return 0 if errores == 0 else 1


if __name__ == "__main__":

    sys.exit(
        main()
    )