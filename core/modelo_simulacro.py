"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : modelo_simulacro.py
Ruta    : core/modelo_simulacro.py

Objetivo:
    Definir los modelos internos de opción, pregunta y simulacro.

Entradas:
    - Datos normalizados del simulacro.

Salidas:
    - Objetos Opcion, Pregunta y Simulacro.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - core/normalizar_simulacro.py

Flujo:
    1. Define estructuras de datos.
    2. Calcula el total de preguntas.

Observaciones:
    - Ninguna.

==============================================================================
"""
from dataclasses import (
    dataclass,
    field,
)


@dataclass
class Opcion:

    letra: str

    texto: str


@dataclass
class Pregunta:

    numero: int

    enunciado: str

    opciones: list[Opcion]

    respuesta_correcta: str

    tipo_pregunta: str

    tema: int | None

    norma: str |None

    articulo: str | None

    origen: str

    texto_respuesta_correcta: str | None = None

    fragmento: dict | None = None

    explicacion: dict | None = None


@dataclass
class Simulacro:

    preguntas: list[Pregunta] = field(
        default_factory=list
    )

    completo: bool = False

    preguntas_ia: int = 0

    @property
    def total(
        self,
    ):

        return len(
            self.preguntas
        )