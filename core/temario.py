"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Core
Estado   : OK

Archivo : temario.py
Ruta    : core/temario.py

Objetivo:
    Cargar y consultar la definición de una convocatoria desde su CFG.

Entradas:
    - Código o fichero CFG de convocatoria.

Salidas:
    - Partes, temas, documentos, coberturas y distribución.

Modifica BD:
    No

Tablas afectadas:
    - Ninguna.

Utiliza:
    - core.normas

Utilizado por:
    - core/buscar_documentos_informatica.py
    - core/buscar_fragmentos.py
    - core/clasificador.py
    - core/validar_pie.py
    - procesos/actualizar_documentos.py
    - procesos/clasificar_modelo.py
    - procesos/clasificar_pendientes.py
    - procesos/clasificar_pregunta.py
    - procesos/importar_json_extraido.py

Flujo:
    1. Lee la configuración.
    2. Identifica normas y coberturas.
    3. Expone consultas.

Observaciones:
    - Ninguna.

==============================================================================
"""
import configparser
import re
import unicodedata
from pathlib import Path

from core.normas import cargar_normas


RUTA_CFG_DEFAULT = Path("config/C1-01_58_26.cfg")


def normalizar(texto):

    texto = unicodedata.normalize(
        "NFD",
        (texto or "").lower(),
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


def normalizar_articulo(articulo):

    if articulo is None:
        return None

    texto = str(articulo).strip().lower()

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    coincidencia = re.fullmatch(
        r"(\d+)"
        r"(?:\s*(bis|ter|quater))?",
        texto,
    )

    if coincidencia is None:
        raise ValueError(
            f"Artículo no válido: {articulo}"
        )

    numero = int(coincidencia.group(1))
    sufijo = coincidencia.group(2)

    if sufijo:
        return f"{numero} {sufijo}"

    return str(numero)


def expandir_articulos(expresion):

    articulos = set()

    expresion_original = expresion
    expresion = expresion.lower().strip()

    expresion = expresion.replace(",", " y ")

    partes = re.split(
        r"\s+y\s+",
        expresion,
    )

    for parte in partes:

        parte = parte.strip()

        if not parte:
            continue

        rango = re.fullmatch(
            r"(\d+)\s*-\s*(\d+)",
            parte,
        )

        if rango:

            inicio = int(rango.group(1))
            fin = int(rango.group(2))

            if fin < inicio:
                raise ValueError(
                    f"Rango de artículos inválido: "
                    f"{expresion_original}"
                )

            for numero in range(
                inicio,
                fin + 1,
            ):
                articulos.add(str(numero))

            continue

        articulo = re.fullmatch(
            r"(\d+)"
            r"(?:\s*(bis|ter|quater))?",
            parte,
        )

        if articulo:

            numero = articulo.group(1)
            sufijo = articulo.group(2)

            if sufijo:
                articulos.add(
                    f"{numero} {sufijo}"
                )
            else:
                articulos.add(numero)

            continue

        raise ValueError(
            "Expresión de artículos no reconocida: "
            f"{expresion_original}"
        )

    return tuple(
        sorted(
            articulos,
            key=lambda valor: (
                int(valor.split()[0]),
                valor,
            ),
        )
    )


class Temario:

    def __init__(
        self,
        ruta_cfg=RUTA_CFG_DEFAULT,
    ):

        self._ruta_cfg = Path(ruta_cfg)

        if not self._ruta_cfg.exists():
            raise FileNotFoundError(
                f"No existe el CFG: "
                f"{self._ruta_cfg.resolve()}"
            )

        self._cfg = configparser.ConfigParser()
        self._cfg.optionxform = str

        self._cfg.read(
            self._ruta_cfg,
            encoding="utf-8",
        )

        if "CONVOCATORIA" not in self._cfg:
            raise ValueError(
                "El CFG no contiene "
                "[CONVOCATORIA]."
            )

        if "PARTES_TEMARIO" not in self._cfg:
            raise ValueError(
                "El CFG no contiene "
                "[PARTES_TEMARIO]."
            )

        self._catalogo_normas = cargar_normas()

        self._convocatoria = dict(
            self._cfg["CONVOCATORIA"]
        )

        self._partes = {}
        self._temas = {}
        self._documentos = {}
        self._normas = {}
        self._articulos = {}
        self._distribucion = {}

        self._cargar_partes()
        self._cargar_temario()
        self._cargar_distribucion()

    def _cargar_partes(self):

        for orden_texto, nombre in self._cfg[
            "PARTES_TEMARIO"
        ].items():

            orden = int(orden_texto)
            nombre = nombre.strip()

            self._partes[nombre] = {
                "orden": orden,
                "nombre": nombre,
                "clave": normalizar(nombre),
            }

    def _obtener_parte_seccion(
        self,
        seccion,
    ):

        sufijo = seccion.removeprefix(
            "TEMARIO_"
        )

        clave_seccion = normalizar(sufijo)

        for parte in self._partes.values():

            if parte["clave"] == clave_seccion:
                return parte

        raise ValueError(
            f"No se puede relacionar [{seccion}] "
            "con ninguna parte definida en "
            "[PARTES_TEMARIO]."
        )

    def _identificar_norma_documento(
        self,
        nombre_archivo,
    ):

        nombre_normalizado = normalizar(
            Path(nombre_archivo).stem
        )

        coincidencias = []

        for norma in self._catalogo_normas:

            prefijo_normalizado = normalizar(
                norma["prefijo"]
            )

            if nombre_normalizado.startswith(
                prefijo_normalizado
            ):

                coincidencias.append({
                    "longitud": len(
                        prefijo_normalizado
                    ),
                    "codigo": norma["codigo"],
                })

        if not coincidencias:
            return None

        coincidencias.sort(
            key=lambda item: item["longitud"],
            reverse=True,
        )

        return coincidencias[0]["codigo"]

    def _obtener_cobertura_documento(
        self,
        nombre_archivo,
    ):

        nombre = Path(nombre_archivo).stem

        coincidencia = re.search(
            r"\bart[ií]culos?\s+(.+)$",
            nombre,
            re.IGNORECASE,
        )

        if coincidencia is None:

            return {
                "cobertura_completa": True,
                "articulos": None,
            }

        expresion = coincidencia.group(1).strip()

        return {
            "cobertura_completa": False,
            "articulos": expandir_articulos(
                expresion
            ),
        }

    def _cargar_temario(self):

        for seccion in self._cfg.sections():

            if not seccion.startswith(
                "TEMARIO_"
            ):
                continue

            parte = self._obtener_parte_seccion(
                seccion
            )

            for numero_texto, valor in self._cfg[
                seccion
            ].items():

                numero_tema = int(numero_texto)

                piezas = [
                    pieza.strip()
                    for pieza in valor.split("|")
                    if pieza.strip()
                ]

                if len(piezas) < 2:

                    raise ValueError(
                        f"Tema mal definido en "
                        f"[{seccion}] "
                        f"{numero_tema}: {valor}"
                    )

                titulo = piezas[0]
                nombres_documentos = piezas[1:]

                clave_tema = (
                    parte["nombre"],
                    numero_tema,
                )

                if clave_tema in self._temas:

                    raise ValueError(
                        "Tema duplicado: "
                        f"{parte['nombre']} "
                        f"{numero_tema}"
                    )

                tema = {
                    "parte": parte["nombre"],
                    "parte_orden": parte["orden"],
                    "numero": numero_tema,
                    "titulo": titulo,
                    "seccion_cfg": seccion,
                    "documentos": tuple(
                        nombres_documentos
                    ),
                }

                self._temas[clave_tema] = tema

                for nombre_archivo in (
                    nombres_documentos
                ):

                    codigo_norma = (
                        self._identificar_norma_documento(
                            nombre_archivo
                        )
                    )

                    cobertura = (
                        self._obtener_cobertura_documento(
                            nombre_archivo
                        )
                    )

                    asociacion = {
                        "parte": parte["nombre"],
                        "parte_orden": parte["orden"],
                        "tema": numero_tema,
                        "titulo_tema": titulo,
                        "documento": nombre_archivo,
                        "norma": codigo_norma,
                        "cobertura_completa": cobertura[
                            "cobertura_completa"
                        ],
                        "articulos": cobertura[
                            "articulos"
                        ],
                    }

                    self._documentos.setdefault(
                        nombre_archivo,
                        [],
                    ).append(asociacion)

                    if codigo_norma is None:
                        continue

                    self._normas.setdefault(
                        codigo_norma,
                        [],
                    ).append(asociacion)

                    if cobertura[
                        "articulos"
                    ] is None:
                        continue

                    for articulo in cobertura[
                        "articulos"
                    ]:

                        clave_articulo = (
                            codigo_norma,
                            articulo,
                        )

                        self._articulos.setdefault(
                            clave_articulo,
                            [],
                        ).append(asociacion)

    def _cargar_distribucion(self):

        seccion = "DISTRIBUCION_PREGUNTAS"

        if seccion not in self._cfg:
            return

        for nombre_parte, cantidad in self._cfg[
            seccion
        ].items():

            self._distribucion[
                nombre_parte.strip()
            ] = int(cantidad)

    def obtener_convocatoria(self):

        return dict(self._convocatoria)

    def obtener_partes(self):

        return tuple(
            sorted(
                (
                    dict(parte)
                    for parte in self._partes.values()
                ),
                key=lambda parte: parte["orden"],
            )
        )

    def obtener_temas(
        self,
        parte=None,
    ):

        temas = self._temas.values()

        if parte is not None:

            temas = (
                tema
                for tema in temas
                if tema["parte"] == parte
            )

        return tuple(
            dict(tema)
            for tema in sorted(
                temas,
                key=lambda tema: (
                    tema["parte_orden"],
                    tema["numero"],
                ),
            )
        )

    def obtener_tema(
        self,
        parte,
        numero_tema,
    ):

        tema = self._temas.get(
            (
                parte,
                int(numero_tema),
            )
        )

        if tema is None:
            return None

        return dict(tema)

    def obtener_documentos(self):

        return tuple(
            sorted(
                self._documentos.keys()
            )
        )

    def obtener_documentos_norma(
        self,
        codigo_norma,
    ):

        asociaciones = self._normas.get(
            codigo_norma,
            [],
        )

        return tuple(
            sorted({
                asociacion["documento"]
                for asociacion in asociaciones
            })
        )

    def obtener_asociaciones_documento(
        self,
        nombre_archivo,
    ):

        return tuple(
            dict(asociacion)
            for asociacion in self._documentos.get(
                nombre_archivo,
                [],
            )
        )

    def norma_pertenece(
        self,
        codigo_norma,
    ):

        return codigo_norma in self._normas

    def articulo_pertenece(
        self,
        codigo_norma,
        articulo,
    ):

        articulo = normalizar_articulo(
            articulo
        )

        return (
            codigo_norma,
            articulo,
        ) in self._articulos

    def obtener_asociaciones_articulo(
    self,
    codigo_norma,
    articulo,
    ):

        articulo = normalizar_articulo(
            articulo
        )

        asociaciones = list(
            self._articulos.get(
                (
                    codigo_norma,
                    articulo,
                ),
                [],
            )
        )

        for asociacion in self._normas.get(
            codigo_norma,
            [],
        ):

            if (
                asociacion["cobertura_completa"]
                and asociacion not in asociaciones
            ):

                asociaciones.append(
                    asociacion
                )

        return tuple(
            dict(asociacion)
            for asociacion in asociaciones
        )

    def obtener_temas_articulo(
        self,
        codigo_norma,
        articulo,
    ):

        asociaciones = (
            self.obtener_asociaciones_articulo(
                codigo_norma,
                articulo,
            )
        )

        temas = {
            (
                asociacion["parte"],
                asociacion["tema"],
                asociacion["titulo_tema"],
            )
            for asociacion in asociaciones
        }

        return tuple(
            {
                "parte": parte,
                "tema": tema,
                "titulo": titulo,
            }
            for parte, tema, titulo in sorted(
                temas,
                key=lambda item: (
                    self._partes[
                        item[0]
                    ]["orden"],
                    item[1],
                ),
            )
        )

    def obtener_distribucion(self):

        return dict(self._distribucion)

    def obtener_numero_preguntas(self):

        normas_examen = "NORMAS_EXAMEN"

        if normas_examen not in self._cfg:
            return None

        valor = self._cfg[
            normas_examen
        ].get(
            "numero_preguntas"
        )

        if valor is None:
            return None

        return int(valor)

    def es_informatica(
        self,
        parte,
        numero_tema,
    ):

        tema = self.obtener_tema(
            parte,
            numero_tema,
        )

        if tema is None:
            return False

        return "informatica" in normalizar(
            tema["parte"]
        )

    def resumen(self):

        return {
            "ruta_cfg": str(
                self._ruta_cfg
            ),
            "partes": len(
                self._partes
            ),
            "temas": len(
                self._temas
            ),
            "documentos": len(
                self._documentos
            ),
            "normas": len(
                self._normas
            ),
            "articulos_indexados": len(
                self._articulos
            ),
        }


def main():

    temario = Temario()

    resumen = temario.resumen()

    print()
    print("=" * 70)
    print("TEMARIO DE LA CONVOCATORIA")
    print("=" * 70)
    print(
        f"CFG................: "
        f"{resumen['ruta_cfg']}"
    )
    print(
        f"Partes.............: "
        f"{resumen['partes']}"
    )
    print(
        f"Temas..............: "
        f"{resumen['temas']}"
    )
    print(
        f"Documentos.........: "
        f"{resumen['documentos']}"
    )
    print(
        f"Normas.............: "
        f"{resumen['normas']}"
    )
    print(
        f"Artículos indexados: "
        f"{resumen['articulos_indexados']}"
    )

    print()
    print("PRUEBAS DE CONSULTA")
    print("-" * 70)

    pruebas = [
        ("L39_2015", 1),
        ("L39_2015", 52),
        ("L39_2015", 126),
        ("L6_2025", 10),
        ("L6_2025", 24),
        ("LO2_1982", 12),
    ]

    for norma, articulo in pruebas:

        pertenece = (
            temario.articulo_pertenece(
                norma,
                articulo,
            )
        )

        print(
            f"{norma:<12} "
            f"art. {articulo:<4} "
            f"{'SÍ' if pertenece else 'NO'}"
        )


if __name__ == "__main__":
    main()