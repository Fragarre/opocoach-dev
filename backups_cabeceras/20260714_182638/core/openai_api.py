"""
Archivo: openai_api.py
Ruta: core/openai_api.py

Dependencias:
- csv
- os
- time
- datetime
- pathlib
- dotenv
- openai

Funcionalidad:
Centraliza la comunicación con la API de OpenAI.

Proporciona funciones para:

- enviar prompts al modelo seleccionado;
- obtener la respuesta en texto o JSON;
- registrar métricas de utilización;
- calcular el coste estimado de cada consulta;
- mantener un histórico de costes en formato CSV.

Este módulo no contiene lógica de negocio ni toma decisiones sobre la
clasificación de preguntas. Su única responsabilidad es gestionar la
comunicación con la API de OpenAI y el registro asociado.

No modifica la base de datos.
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

cliente = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY_OPOCOACH")
)


PRECIOS = {
    "gpt-5-mini": {
        "input": 0.75,
        "output": 4.50,
    },
    "gpt-5.4": {
        "input": 2.50,
        "output": 15.00,
    },
    "gpt-5.4-mini": {
        "input": 0.75,
        "output": 4.50,
    },
}


LOG_COSTES = Path("logs/costes_ia.csv")


def registrar_coste(
    modelo,
    operacion,
    tiempo,
    input_tokens,
    cached_tokens,
    output_tokens,
    coste,
):

    LOG_COSTES.parent.mkdir(exist_ok=True)

    existe = LOG_COSTES.exists()

    with LOG_COSTES.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        if not existe:
            writer.writerow([
                "fecha",
                "hora",
                "modelo",
                "operacion",
                "tiempo",
                "input",
                "cached_input",
                "output",
                "coste",
            ])

        ahora = datetime.now()

        writer.writerow([
            ahora.strftime("%Y-%m-%d"),
            ahora.strftime("%H:%M:%S"),
            modelo,
            operacion,
            f"{tiempo:.2f}",
            input_tokens,
            cached_tokens,
            output_tokens,
            f"{coste:.6f}",
        ])


def seleccionar_fragmento(
    prompt,
    modelo="gpt-5.4-mini",
    operacion="general",
):

    t0 = time.perf_counter()

    respuesta = cliente.responses.create(
        model=modelo,
        input=prompt,
    )

    tiempo = time.perf_counter() - t0

    uso = respuesta.usage

    entrada = uso.input_tokens
    salida = uso.output_tokens

    cached = 0

    try:
        cached = uso.input_tokens_details.cached_tokens
    except Exception:
        pass

    precio = PRECIOS[modelo]

    coste = (
        entrada * precio["input"] / 1_000_000
        +
        salida * precio["output"] / 1_000_000
    )

    registrar_coste(
        modelo=modelo,
        operacion=operacion,
        tiempo=tiempo,
        input_tokens=entrada,
        cached_tokens=cached,
        output_tokens=salida,
        coste=coste,
    )

    print()
    print("=" * 60)
    print("IA")
    print("=" * 60)
    print(f"Modelo............. {modelo}")
    print(f"Tiempo............. {tiempo:.2f} s")
    print(f"Input.............. {entrada}")
    print(f"Cached............. {cached}")
    print(f"Output............. {salida}")
    print(f"Coste.............. ${coste:.6f}")
    print()

    return respuesta.output_text

def seleccionar_fragmento_json(
    prompt,
    modelo="gpt-5.4-mini",
    operacion="general",
):

    import json

    respuesta = seleccionar_fragmento(
        prompt=prompt,
        modelo=modelo,
        operacion=operacion,
    )
    
    return json.loads(respuesta)

def generar_explicacion_ia(
    prompt,
    modelo="gpt-5.4-mini",
):

    return seleccionar_fragmento_json(
        prompt=prompt,
        modelo=modelo,
        operacion="explicacion",
    )