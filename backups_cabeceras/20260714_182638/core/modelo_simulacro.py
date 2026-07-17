"""
Archivo: modelo_simulacro.py
Ruta: core/modelo_simulacro.py

Modelo interno de un simulacro.

No conoce JSON, PDF, HTML ni la base de datos.
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