"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : huellas.py
Ruta    : core/huellas.py

Objetivo:
    Calcular huellas estables de preguntas para detectar duplicados.

Entradas:
    - Enunciado.
    - Opciones A-D.

Salidas:
    - Hash normalizado de la pregunta.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - procesos/generar_explicaciones.py
    - procesos/importar_json_extraido.py

Flujo:
    1. Normaliza textos.
    2. Concatena el contenido.
    3. Calcula SHA-256.

Observaciones:
    - Ninguna.

==============================================================================
"""
import hashlib


def calcular_huella(
    enunciado,
    opciones,
):

    texto = enunciado.strip()

    for letra in ("A", "B", "C", "D"):

        texto += "\n"
        texto += opciones[letra].strip()

    return hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()