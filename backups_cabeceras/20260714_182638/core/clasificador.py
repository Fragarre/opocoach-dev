"""
Archivo: clasificador.py
Ruta: core/clasificador.py

Dependencias:
- re
- core.buscar_documentos_informatica
- core.buscar_fragmentos
- core.normas
- core.openai_api
- core.prompt_seleccionar_documento
- core.prompt_seleccionar_fragmento
- core.temario

Funcionalidad:
Implementa el Proceso 3 de clasificación de preguntas.

Rama normativa:
- clasificación determinista;
- recuperación de fragmentos mediante BM25;
- validación documental mediante IA;
- asignación de norma, artículo, parte y tema mediante Temario.

Rama de Informática:
- recuperación de documentos mediante BM25;
- validación documental mediante IA;
- asignación de parte y tema mediante Temario.

BM25 únicamente recupera candidatos.

La IA únicamente determina si la evidencia suministrada justifica la
respuesta oficial.

No modifica la base de datos.
"""

import re

from core.buscar_documentos_informatica import (
    buscar_documentos_informatica,
)
from core.buscar_fragmentos import buscar_fragmentos
from core.normas import cargar_normas, detectar_normas
from core.openai_api import seleccionar_fragmento_json
from core.prompt_seleccionar_documento import (
    construir_prompt_seleccionar_documento,
)
from core.prompt_seleccionar_fragmento import construir_prompt
from core.temario import Temario


PATRON_ARTICULO = re.compile(
    r"\bart[íi]culo(?:s)?\s+"
    r"(?P<numero>\d+)"
    r"(?:\s*(?P<sufijo>bis|ter|quater))?",
    re.IGNORECASE,
)


PATRON_NORMA_GENERICA = re.compile(
    r"\b"
    r"(?P<tipo>"
    r"ley\s+org[aá]nica"
    r"|real\s+decreto\s+legislativo"
    r"|decreto\s+legislativo"
    r"|ley"
    r"|decreto"
    r")"
    r"\s+"
    r"(?P<numero>\d+)"
    r"\s*/\s*"
    r"(?P<anio>\d{4})"
    r"\b",
    re.IGNORECASE,
)

PATRON_NORMA_NOMINADA = re.compile(
    r"\bc[oó]digo\s+civil\b",
    re.IGNORECASE,
)

ESTADOS_VALIDOS = {
    "VALIDADA",
    "A_REVISAR",
    "RECHAZADA",
}


def detectar_articulo(texto):

    coincidencia = PATRON_ARTICULO.search(
        texto or ""
    )

    if coincidencia is None:
        return None

    numero = coincidencia.group("numero")
    sufijo = coincidencia.group("sufijo")

    if sufijo:
        return f"{numero} {sufijo.lower()}"

    return numero


def detectar_norma_generica(texto):

    coincidencia = PATRON_NORMA_GENERICA.search(
        texto or ""
    )

    if coincidencia is None:
        return None

    tipo = coincidencia.group("tipo").lower()
    numero = coincidencia.group("numero")
    anio = coincidencia.group("anio")

    tipo = re.sub(
        r"\s+",
        " ",
        tipo,
    )

    if tipo in {
        "ley orgánica",
        "ley organica",
    }:
        prefijo = "LO"

    elif tipo in {
        "decreto legislativo",
        "real decreto legislativo",
    }:
        prefijo = "DL"

    elif tipo == "decreto":
        prefijo = "D"

    else:
        prefijo = "L"

    return f"{prefijo}{numero}_{anio}"

def detectar_norma_nominada(texto):

    if PATRON_NORMA_NOMINADA.search(
        texto or ""
    ):
        return "CODIGO_CIVIL"

    return None

def crear_resultado(
    *,
    resuelta,
    estado,
    norma=None,
    articulo=None,
    parte=None,
    tema=None,
    temas_compatibles=(),
    fragmento_id=None,
    documento=None,
    confianza=None,
    metodo_validacion=None,
    motivo="",
):

    return {
        "resuelta": resuelta,
        "estado": estado,
        "norma": norma,
        "articulo": articulo,
        "parte": parte,
        "tema": tema,
        "temas_compatibles": temas_compatibles,
        "fragmento_id": fragmento_id,
        "documento": documento,
        "confianza": confianza,
        "metodo_validacion": metodo_validacion,
        "motivo": motivo,
    }


class Clasificador:

    def __init__(
        self,
        temario,
        normas=None,
    ):

        if not isinstance(
            temario,
            Temario,
        ):
            raise TypeError(
                "temario debe ser una instancia de Temario."
            )

        self.temario = temario

        self.normas = (
            normas
            if normas is not None
            else cargar_normas()
        )

    def detectar_referencias(
        self,
        enunciado,
    ):

        normas_detectadas = detectar_normas(
            enunciado,
            self.normas,
        )

        codigos_normas = tuple(
            norma["codigo"]
            for norma in normas_detectadas
        )

        if not codigos_normas:

            norma_nominada = detectar_norma_nominada(
                enunciado
            )

            if norma_nominada is not None:

                codigos_normas = (
                    norma_nominada,
                )

            else:

                norma_generica = detectar_norma_generica(
                    enunciado
                )

                if norma_generica is not None:

                    codigos_normas = (
                        norma_generica,
                    )

        articulo = detectar_articulo(
            enunciado
        )

        return {
            "normas": codigos_normas,
            "articulo": articulo,
        }
    def clasificar_directa(
        self,
        enunciado,
    ):

        referencias = self.detectar_referencias(
            enunciado
        )

        normas = referencias["normas"]
        articulo = referencias["articulo"]

        if len(normas) == 0:

            return crear_resultado(
                resuelta=False,
                estado="PENDIENTE",
                articulo=articulo,
                motivo=(
                    "No se ha detectado una norma explícita."
                ),
            )

        if len(normas) > 1:

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                confianza=1.0,
                metodo_validacion="DIRECTA",
                motivo=(
                    "La pregunta hace referencia a varias "
                    "normas distintas y no sigue el formato "
                    "admitido por el proyecto."
                ),
            )

        norma = normas[0]

        if not self.temario.norma_pertenece(
            norma
        ):

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                norma=norma,
                articulo=articulo,
                confianza=1.0,
                metodo_validacion="DIRECTA",
                motivo=(
                    "La norma citada no pertenece "
                    "al temario."
                ),
            )

        if articulo is None:

            return crear_resultado(
                resuelta=False,
                estado="PENDIENTE",
                norma=norma,
                motivo=(
                    "La norma pertenece al temario, "
                    "pero no se cita artículo."
                ),
            )

        if not self.temario.articulo_pertenece(
            norma,
            articulo,
        ):

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                norma=norma,
                articulo=articulo,
                confianza=1.0,
                metodo_validacion="DIRECTA",
                motivo=(
                    "La norma pertenece al temario, "
                    "pero el artículo citado no está incluido."
                ),
            )

        temas = self.temario.obtener_temas_articulo(
            norma,
            articulo,
        )

        if len(temas) == 1:

            tema = temas[0]

            return crear_resultado(
                resuelta=True,
                estado="VALIDADA",
                norma=norma,
                articulo=articulo,
                parte=tema["parte"],
                tema=tema["tema"],
                temas_compatibles=temas,
                confianza=1.0,
                metodo_validacion="DIRECTA",
                motivo=(
                    "La norma y el artículo citados "
                    "pertenecen al temario."
                ),
            )

        return crear_resultado(
            resuelta=True,
            estado="A_REVISAR",
            norma=norma,
            articulo=articulo,
            temas_compatibles=temas,
            confianza=1.0,
            metodo_validacion="DIRECTA",
            motivo=(
                "La norma y el artículo pertenecen "
                "al temario, pero están asociados "
                "a varios temas."
            ),
        )

    def _validar_opciones(
        self,
        opciones,
    ):

        if not isinstance(
            opciones,
            dict,
        ):
            raise TypeError(
                "opciones debe ser un diccionario."
            )

        for letra in (
            "A",
            "B",
            "C",
            "D",
        ):

            if letra not in opciones:
                raise ValueError(
                    f"Falta la opción {letra}."
                )

            if not str(
                opciones[letra]
            ).strip():
                raise ValueError(
                    f"La opción {letra} está vacía."
                )

    def _validar_respuesta_correcta(
        self,
        respuesta_correcta,
    ):

        respuesta = str(
            respuesta_correcta
        ).strip().upper()

        if respuesta not in {
            "A",
            "B",
            "C",
            "D",
        }:
            raise ValueError(
                "respuesta_correcta debe ser "
                "A, B, C o D."
            )

        return respuesta

    def _aplicar_umbrales(
        self,
        decision,
        confianza,
    ):

        if decision == "RECHAZADA":
            return "RECHAZADA"

        if confianza < 0.50:
            return "RECHAZADA"

        if decision == "A_REVISAR":
            return "A_REVISAR"

        if confianza < 0.95:
            return "A_REVISAR"

        return "VALIDADA"

    def _obtener_fragmento_seleccionado(
        self,
        fragmentos,
        fragmento_id,
    ):

        for fragmento in fragmentos:

            if fragmento[
                "fragmento_id"
            ] == fragmento_id:
                return fragmento

        return None

    def _validar_respuesta_ia_fragmento(
        self,
        respuesta_ia,
        fragmentos,
    ):

        if not isinstance(
            respuesta_ia,
            dict,
        ):
            raise ValueError(
                "La respuesta de la IA no es "
                "un objeto JSON."
            )

        decision = str(
            respuesta_ia.get(
                "decision",
                "",
            )
        ).strip().upper()

        if decision not in ESTADOS_VALIDOS:
            raise ValueError(
                f"Decisión IA no válida: {decision}"
            )

        confianza = respuesta_ia.get(
            "confianza"
        )

        if not isinstance(
            confianza,
            (
                int,
                float,
            ),
        ):
            raise ValueError(
                "La confianza de la IA no es numérica."
            )

        confianza = float(confianza)

        if not 0.0 <= confianza <= 1.0:
            raise ValueError(
                "La confianza debe estar entre 0 y 1."
            )

        motivo = str(
            respuesta_ia.get(
                "motivo",
                "",
            )
        ).strip()

        fragmento_id = respuesta_ia.get(
            "fragmento_id"
        )

        if decision == "RECHAZADA":

            if fragmento_id is not None:
                raise ValueError(
                    "Una respuesta RECHAZADA debe "
                    "tener fragmento_id null."
                )

            return {
                "decision": decision,
                "confianza": confianza,
                "motivo": motivo,
                "fragmento": None,
            }

        if not isinstance(
            fragmento_id,
            int,
        ):
            raise ValueError(
                "fragmento_id debe ser un entero."
            )

        fragmento = (
            self._obtener_fragmento_seleccionado(
                fragmentos,
                fragmento_id,
            )
        )

        if fragmento is None:
            raise ValueError(
                "La IA ha seleccionado un fragmento "
                "que no estaba entre los candidatos."
            )

        return {
            "decision": decision,
            "confianza": confianza,
            "motivo": motivo,
            "fragmento": fragmento,
        }

    def _obtener_asociaciones_fragmento(
        self,
        fragmento,
    ):

        asociaciones = (
            self.temario.obtener_asociaciones_documento(
                fragmento["nombre_archivo"]
            )
        )

        articulo = fragmento.get(
            "articulo"
        )

        if articulo in {
            None,
            "",
        }:
            return asociaciones

        filtradas = tuple(
            asociacion
            for asociacion in asociaciones
            if (
                asociacion["cobertura_completa"]
                or (
                    asociacion["articulos"] is not None
                    and str(articulo)
                    in asociacion["articulos"]
                )
            )
        )

        if filtradas:
            return filtradas

        return asociaciones

    def _construir_resultado_fragmento(
        self,
        validacion_ia,
    ):

        estado = self._aplicar_umbrales(
            decision=validacion_ia["decision"],
            confianza=validacion_ia["confianza"],
        )

        confianza = validacion_ia["confianza"]
        motivo = validacion_ia["motivo"]
        fragmento = validacion_ia["fragmento"]

        if estado == "RECHAZADA":

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                confianza=confianza,
                metodo_validacion="BM25_IA",
                motivo=motivo,
            )

        asociaciones = (
            self._obtener_asociaciones_fragmento(
                fragmento
            )
        )

        if not asociaciones:

            return crear_resultado(
                resuelta=True,
                estado="A_REVISAR",
                fragmento_id=fragmento[
                    "fragmento_id"
                ],
                documento=fragmento[
                    "nombre_archivo"
                ],
                confianza=confianza,
                metodo_validacion="BM25_IA",
                motivo=(
                    "El fragmento fue seleccionado, "
                    "pero no pudo relacionarse con "
                    "el temario."
                ),
            )

        temas = {
            (
                asociacion["parte"],
                asociacion["tema"],
                asociacion["titulo_tema"],
                asociacion["norma"],
            )
            for asociacion in asociaciones
        }

        temas_compatibles = tuple(
            {
                "parte": parte,
                "tema": tema,
                "titulo": titulo,
                "norma": norma,
            }
            for parte, tema, titulo, norma in sorted(
                temas,
                key=lambda item: (
                    item[0],
                    item[1],
                ),
            )
        )

        normas = {
            asociacion["norma"]
            for asociacion in asociaciones
            if asociacion["norma"] is not None
        }

        norma = (
            next(iter(normas))
            if len(normas) == 1
            else None
        )

        articulo = fragmento.get(
            "articulo"
        )

        if len(temas_compatibles) != 1:

            return crear_resultado(
                resuelta=True,
                estado="A_REVISAR",
                norma=norma,
                articulo=articulo,
                temas_compatibles=temas_compatibles,
                fragmento_id=fragmento[
                    "fragmento_id"
                ],
                documento=fragmento[
                    "nombre_archivo"
                ],
                confianza=confianza,
                metodo_validacion="BM25_IA",
                motivo=(
                    "El fragmento respalda la respuesta, "
                    "pero está asociado a varios temas."
                ),
            )

        tema = temas_compatibles[0]

        return crear_resultado(
            resuelta=True,
            estado=estado,
            norma=tema["norma"],
            articulo=articulo,
            parte=tema["parte"],
            tema=tema["tema"],
            temas_compatibles=temas_compatibles,
            fragmento_id=fragmento[
                "fragmento_id"
            ],
            documento=fragmento[
                "nombre_archivo"
            ],
            confianza=confianza,
            metodo_validacion="BM25_IA",
            motivo=motivo,
        )

    def _obtener_documento_seleccionado(
        self,
        documentos,
        documento_id,
    ):

        for documento in documentos:

            if documento[
                "documento_id"
            ] == documento_id:
                return documento

        return None

    def _validar_respuesta_ia_documento(
        self,
        respuesta_ia,
        documentos,
    ):

        if not isinstance(
            respuesta_ia,
            dict,
        ):
            raise ValueError(
                "La respuesta de la IA no es "
                "un objeto JSON."
            )

        decision = str(
            respuesta_ia.get(
                "decision",
                "",
            )
        ).strip().upper()

        if decision not in ESTADOS_VALIDOS:
            raise ValueError(
                f"Decisión IA no válida: {decision}"
            )

        confianza = respuesta_ia.get(
            "confianza"
        )

        if not isinstance(
            confianza,
            (
                int,
                float,
            ),
        ):
            raise ValueError(
                "La confianza de la IA no es numérica."
            )

        confianza = float(confianza)

        if not 0.0 <= confianza <= 1.0:
            raise ValueError(
                "La confianza debe estar entre 0 y 1."
            )

        motivo = str(
            respuesta_ia.get(
                "motivo",
                "",
            )
        ).strip()

        documento_id = respuesta_ia.get(
            "documento_id"
        )

        if decision == "RECHAZADA":

            if documento_id is not None:
                raise ValueError(
                    "Una respuesta RECHAZADA debe "
                    "tener documento_id null."
                )

            return {
                "decision": decision,
                "confianza": confianza,
                "motivo": motivo,
                "documento": None,
            }

        if not isinstance(
            documento_id,
            int,
        ):
            raise ValueError(
                "documento_id debe ser un entero."
            )

        documento = (
            self._obtener_documento_seleccionado(
                documentos,
                documento_id,
            )
        )

        if documento is None:
            raise ValueError(
                "La IA ha seleccionado un documento "
                "que no estaba entre los candidatos."
            )

        return {
            "decision": decision,
            "confianza": confianza,
            "motivo": motivo,
            "documento": documento,
        }

    def _construir_resultado_documento(
        self,
        validacion_ia,
    ):

        estado = self._aplicar_umbrales(
            decision=validacion_ia["decision"],
            confianza=validacion_ia["confianza"],
        )

        confianza = validacion_ia["confianza"]
        motivo = validacion_ia["motivo"]
        documento = validacion_ia["documento"]

        if estado == "RECHAZADA":

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                confianza=confianza,
                metodo_validacion="BM25_IA_DOCUMENTO",
                motivo=motivo,
            )

        asociaciones = documento[
            "asociaciones"
        ]

        temas = {
            (
                asociacion["parte"],
                asociacion["tema"],
                asociacion["titulo_tema"],
            )
            for asociacion in asociaciones
        }

        temas_compatibles = tuple(
            {
                "parte": parte,
                "tema": tema,
                "titulo": titulo,
            }
            for parte, tema, titulo in sorted(
                temas,
                key=lambda item: (
                    item[0],
                    item[1],
                ),
            )
        )

        if len(temas_compatibles) != 1:

            return crear_resultado(
                resuelta=True,
                estado="A_REVISAR",
                temas_compatibles=temas_compatibles,
                documento=documento[
                    "nombre_archivo"
                ],
                confianza=confianza,
                metodo_validacion="BM25_IA_DOCUMENTO",
                motivo=(
                    "El documento respalda la respuesta, "
                    "pero está asociado a varios temas."
                ),
            )

        tema = temas_compatibles[0]

        return crear_resultado(
            resuelta=True,
            estado=estado,
            parte=tema["parte"],
            tema=tema["tema"],
            temas_compatibles=temas_compatibles,
            documento=documento[
                "nombre_archivo"
            ],
            confianza=confianza,
            metodo_validacion="BM25_IA_DOCUMENTO",
            motivo=motivo,
        )

    def _clasificar_informatica(
        self,
        conn,
        pregunta,
        opciones,
        respuesta_correcta,
        limite_documentos,
        modelo,
    ):

        texto_consulta = (
            pregunta
            + "\n"
            + opciones[
                respuesta_correcta
            ]
        )

        documentos = buscar_documentos_informatica(
            conn=conn,
            temario=self.temario,
            texto_consulta=texto_consulta,
            limite=limite_documentos,
        )

        if not documentos:

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                confianza=0.0,
                metodo_validacion="BM25_DOCUMENTO",
                motivo=(
                    "BM25 no ha localizado documentos "
                    "candidatos de Informática."
                ),
            )

        prompt = construir_prompt_seleccionar_documento(
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta=respuesta_correcta,
            documentos=documentos,
        )

        try:

            respuesta_ia = seleccionar_fragmento_json(
                prompt=prompt,
                modelo=modelo,
                operacion="clasificacion_informatica",
            )

            validacion_ia = (
                self._validar_respuesta_ia_documento(
                    respuesta_ia=respuesta_ia,
                    documentos=documentos,
                )
            )

        except Exception as error:

            return crear_resultado(
                resuelta=True,
                estado="A_REVISAR",
                confianza=None,
                metodo_validacion="BM25_IA_DOCUMENTO",
                motivo=(
                    "No se pudo interpretar de forma "
                    "segura la respuesta de la IA: "
                    f"{error}"
                ),
            )

        return self._construir_resultado_documento(
            validacion_ia
        )

    def clasificar(
        self,
        conn,
        pregunta,
        opciones,
        respuesta_correcta,
        limite_fragmentos=5,
        modelo="gpt-5.4-mini",
        parte_origen=None,
    ):

        if conn is None:
            raise ValueError(
                "conn no puede ser None."
            )

        pregunta = str(
            pregunta or ""
        ).strip()

        if not pregunta:
            raise ValueError(
                "La pregunta está vacía."
            )

        self._validar_opciones(
            opciones
        )

        respuesta_correcta = (
            self._validar_respuesta_correcta(
                respuesta_correcta
            )
        )

        parte_normalizada = str(
            parte_origen or ""
        ).strip().lower()

        if (
            "informática" in parte_normalizada
            or "informatica" in parte_normalizada
        ):

            return self._clasificar_informatica(
                conn=conn,
                pregunta=pregunta,
                opciones=opciones,
                respuesta_correcta=respuesta_correcta,
                limite_documentos=limite_fragmentos,
                modelo=modelo,
            )

        resultado_directo = self.clasificar_directa(
            pregunta
        )

        if resultado_directo[
            "resuelta"
        ]:

            return resultado_directo

        codigo_norma = resultado_directo[
            "norma"
        ]

        texto_consulta = (
            pregunta
            + "\n"
            + opciones[
                respuesta_correcta
            ]
        )

        fragmentos = buscar_fragmentos(
            conn=conn,
            temario=self.temario,
            texto_consulta=texto_consulta,
            codigo_norma=codigo_norma,
            limite=limite_fragmentos,
        )

        if not fragmentos:

            return crear_resultado(
                resuelta=True,
                estado="RECHAZADA",
                norma=codigo_norma,
                confianza=0.0,
                metodo_validacion="BM25",
                motivo=(
                    "BM25 no ha localizado fragmentos "
                    "candidatos dentro del temario."
                ),
            )

        prompt = construir_prompt(
            pregunta=pregunta,
            opciones=opciones,
            respuesta_correcta=respuesta_correcta,
            fragmentos=fragmentos,
        )

        try:

            respuesta_ia = seleccionar_fragmento_json(
                prompt=prompt,
                modelo=modelo,
                operacion="clasificacion_pregunta",
            )

            validacion_ia = (
                self._validar_respuesta_ia_fragmento(
                    respuesta_ia=respuesta_ia,
                    fragmentos=fragmentos,
                )
            )

        except Exception as error:

            return crear_resultado(
                resuelta=True,
                estado="A_REVISAR",
                norma=codigo_norma,
                confianza=None,
                metodo_validacion="BM25_IA",
                motivo=(
                    "No se pudo interpretar de forma "
                    "segura la respuesta de la IA: "
                    f"{error}"
                ),
            )

        return self._construir_resultado_fragmento(
            validacion_ia
        )