"""
==============================================================================
Proyecto : OpoCoach
Tipo     : Proceso
Estado   : OK

Archivo : documentar_scripts.py
Ruta    : procesos/documentar_scripts.py

Objetivo:
    Auditar, normalizar y documentar los scripts Python del proyecto.

Entradas:
    - Scripts Python de core, procesos y render.

Salidas:
    - Cabeceras, inventario e informe de auditoría.

Modifica BD:
    Sí

Tablas afectadas:
    - Ninguna.

Utiliza:
    - Ninguna.

Utilizado por:
    - Ninguna.

Flujo:
    1. Analiza scripts.
    2. Actualiza cabeceras.
    3. Audita.
    4. Genera documentación.

Observaciones:
    - Ninguna.

==============================================================================
"""
import argparse
import ast
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CARPETAS_CODIGO = (
    ROOT / "core",
    ROOT / "procesos",
    ROOT / "render",
)

RUTA_SCRIPTS = ROOT / "docs" / "04_SCRIPTS.md"
RUTA_CABECERAS = ROOT / "docs" / "CABECERAS_PENDIENTES.md"
RUTA_BACKUPS = ROOT / "backups_cabeceras"

CAMPOS_OBLIGATORIOS = (
    "Proyecto",
    "Tipo",
    "Estado",
    "Archivo",
    "Ruta",
    "Objetivo",
    "Entradas",
    "Salidas",
    "Modifica BD",
    "Tablas afectadas",
    "Utiliza",
    "Utilizado por",
    "Flujo",
    "Observaciones",
)

TIPOS_VALIDOS = {"Core", "Proceso", "Utilidad"}
ESTADOS_VALIDOS = {"OK", "REV", "DES", "OBS"}

PALABRAS_SQL_ESCRITURA = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "CREATE TABLE",
    "ALTER TABLE",
    "DROP TABLE",
    "REPLACE INTO",
)

METADATOS = {
    "core/buscar_documentos_informatica.py": {
        "objetivo": "Localizar documentos de informática relevantes para una pregunta.",
        "entradas": ["Texto de la pregunta.", "Configuración de la convocatoria."],
        "salidas": ["Documentos de informática ordenados por relevancia."],
        "flujo": [
            "Carga los documentos de informática.",
            "Normaliza y tokeniza el texto.",
            "Calcula coincidencias.",
            "Devuelve los documentos más relevantes.",
        ],
    },
    "core/buscar_explicacion.py": {
        "objetivo": "Recuperar una explicación existente mediante la huella de la pregunta.",
        "entradas": ["Huella de la pregunta.", "Conexión SQLite."],
        "salidas": ["Explicación reutilizable o None."],
        "flujo": ["Consulta la tabla de explicaciones.", "Devuelve la coincidencia encontrada."],
    },
    "core/buscar_fragmentos.py": {
        "objetivo": "Buscar fragmentos normativos relevantes para una pregunta.",
        "entradas": ["Texto de búsqueda.", "Tema o norma opcionales."],
        "salidas": ["Fragmentos ordenados por relevancia."],
        "flujo": [
            "Limita los documentos aplicables.",
            "Normaliza y tokeniza el texto.",
            "Calcula relevancia.",
            "Devuelve los mejores fragmentos.",
        ],
    },
    "core/clasificador.py": {
        "objetivo": "Validar y clasificar temáticamente preguntas importadas.",
        "entradas": ["Pregunta completa.", "Temario de la convocatoria."],
        "salidas": ["Estado, parte, tema, norma, artículo y trazabilidad."],
        "flujo": [
            "Detecta referencias normativas.",
            "Busca documentos o fragmentos candidatos.",
            "Recurre a IA cuando es necesario.",
            "Aplica umbrales y devuelve la clasificación.",
        ],
    },
    "core/constructor_simulacro.py": {
        "objetivo": "Construir un simulacro con la distribución oficial de la convocatoria.",
        "entradas": ["Distribución del modelo.", "Banco de preguntas."],
        "salidas": ["Simulacro estructurado y relación de faltantes."],
        "flujo": [
            "Carga la distribución.",
            "Selecciona preguntas por tipo y tema.",
            "Evita repeticiones.",
            "Completa faltantes cuando es posible.",
        ],
    },
    "core/construir_prompt_explicacion.py": {
        "objetivo": "Construir el prompt para generar la explicación de una pregunta.",
        "entradas": ["Pregunta.", "Respuesta correcta.", "Fragmento normativo."],
        "salidas": ["Prompt para la API de OpenAI."],
        "flujo": ["Valida los datos.", "Compone las instrucciones y el contexto."],
    },
    "core/distribucion_modelo.py": {
        "objetivo": "Proporcionar la distribución oficial de preguntas por tipo y tema.",
        "entradas": ["Configuración consolidada del examen modelo."],
        "salidas": ["Diccionario de distribución."],
        "flujo": ["Carga la distribución definida.", "Devuelve una copia utilizable."],
    },
    "core/guardar_explicacion.py": {
        "objetivo": "Guardar una explicación generada o reutilizada para una pregunta.",
        "entradas": ["Huella.", "Explicación.", "Metadatos de origen."],
        "salidas": ["Registro persistido en SQLite."],
        "flujo": ["Comprueba la huella.", "Inserta o actualiza la explicación."],
    },
    "core/huellas.py": {
        "objetivo": "Calcular huellas estables de preguntas para detectar duplicados.",
        "entradas": ["Enunciado.", "Opciones A-D."],
        "salidas": ["Hash normalizado de la pregunta."],
        "flujo": ["Normaliza textos.", "Concatena el contenido.", "Calcula SHA-256."],
    },
    "core/modelo_simulacro.py": {
        "objetivo": "Definir los modelos internos de opción, pregunta y simulacro.",
        "entradas": ["Datos normalizados del simulacro."],
        "salidas": ["Objetos Opcion, Pregunta y Simulacro."],
        "flujo": ["Define estructuras de datos.", "Calcula el total de preguntas."],
    },
    "core/normalizar_simulacro.py": {
        "objetivo": "Convertir un JSON de simulacro al modelo interno de renderizado.",
        "entradas": ["Ruta de un JSON de simulacro."],
        "salidas": ["Objeto Simulacro normalizado."],
        "flujo": ["Lee el JSON.", "Valida campos.", "Construye opciones y preguntas."],
    },
    "core/normas.py": {
        "objetivo": "Cargar, normalizar y detectar normas mediante sus alias.",
        "entradas": ["config/normas.csv.", "Texto con referencias normativas."],
        "salidas": ["Catálogo de normas y coincidencias detectadas."],
        "flujo": ["Carga el CSV.", "Normaliza títulos y alias.", "Detecta coincidencias."],
    },
    "core/obtener_fragmento.py": {
        "objetivo": "Recuperar un fragmento normativo por su identificador.",
        "entradas": ["Identificador de fragmento."],
        "salidas": ["Texto y metadatos del fragmento."],
        "flujo": ["Consulta SQLite.", "Devuelve el fragmento completo."],
    },
    "core/openai_api.py": {
        "objetivo": "Centralizar las llamadas a la API de OpenAI y registrar su coste.",
        "entradas": ["Prompt.", "Modelo.", "Parámetros de respuesta."],
        "salidas": ["Respuesta estructurada y métricas de uso."],
        "flujo": ["Carga credenciales.", "Ejecuta la solicitud.", "Registra tokens y coste."],
    },
    "core/prompt_seleccionar_documento.py": {
        "objetivo": "Construir el prompt para seleccionar un documento candidato.",
        "entradas": ["Pregunta.", "Lista de documentos candidatos."],
        "salidas": ["Prompt de selección documental."],
        "flujo": ["Enumera candidatos.", "Define el formato de respuesta."],
    },
    "core/prompt_seleccionar_fragmento.py": {
        "objetivo": "Construir el prompt para seleccionar un fragmento normativo.",
        "entradas": ["Pregunta.", "Fragmentos candidatos."],
        "salidas": ["Prompt de selección de fragmento."],
        "flujo": ["Incluye pregunta y candidatos.", "Define el JSON esperado."],
    },
    "core/render_pdf.py": {
        "objetivo": "Generar el PDF del examen a partir de un simulacro normalizado.",
        "entradas": ["Objeto Simulacro.", "Ruta de salida."],
        "salidas": ["PDF del examen."],
        "flujo": ["Prepara estilos.", "Compone preguntas y opciones.", "Genera el PDF."],
    },
    "core/render_soluciones_pdf.py": {
        "objetivo": "Generar el PDF de soluciones y explicaciones de un simulacro.",
        "entradas": ["Objeto Simulacro.", "Ruta de salida."],
        "salidas": ["PDF de soluciones."],
        "flujo": ["Recupera respuestas.", "Compone soluciones.", "Genera el PDF."],
    },
    "core/selector_banco.py": {
        "objetivo": "Seleccionar preguntas válidas del banco por tipo y tema.",
        "entradas": ["Tipo de pregunta.", "Tema.", "Cantidad.", "IDs excluidos."],
        "salidas": ["Preguntas completas y número de faltantes."],
        "flujo": ["Filtra preguntas válidas.", "Excluye usadas.", "Selecciona aleatoriamente."],
    },
    "core/temario.py": {
        "objetivo": "Cargar y consultar la definición de una convocatoria desde su CFG.",
        "entradas": ["Código o fichero CFG de convocatoria."],
        "salidas": ["Partes, temas, documentos, coberturas y distribución."],
        "flujo": ["Lee la configuración.", "Identifica normas y coberturas.", "Expone consultas."],
    },
    "core/validar_pie.py": {
        "objetivo": "Validar una pregunta mediante la norma y el artículo de su pie.",
        "entradas": ["Referencia normativa.", "Artículo.", "Temario.", "Catálogo de normas."],
        "salidas": ["Estado, norma, artículo, parte, tema y motivo."],
        "flujo": ["Detecta la norma.", "Comprueba cobertura.", "Asigna parte y tema."],
    },
    "procesos/actualizar_documentos.py": {
        "objetivo": "Importar o actualizar documentos del temario y sus fragmentos.",
        "entradas": ["CFG de convocatoria.", "Documentos PDF."],
        "salidas": ["Documentos, relaciones temáticas y fragmentos actualizados."],
        "flujo": ["Carga el CFG.", "Extrae los PDF.", "Fragmenta artículos.", "Actualiza SQLite."],
    },
    "procesos/auditar_scripts.py": {
        "objetivo": "Analizar dependencias y detectar scripts activos, manuales u obsoletos.",
        "entradas": ["Scripts Python del proyecto."],
        "salidas": ["docs/AUDITORIA_SCRIPTS.md."],
        "flujo": ["Analiza imports.", "Relaciona dependencias.", "Clasifica scripts.", "Genera informe."],
    },
    "procesos/calcular_distribucion_modelo.py": {
        "objetivo": "Calcular la distribución del examen modelo por tipo y tema.",
        "entradas": ["Preguntas clasificadas del examen modelo."],
        "salidas": ["Resumen de distribución reutilizable."],
        "flujo": ["Consulta preguntas.", "Agrupa por tipo y tema.", "Muestra el resultado."],
    },
    "procesos/clasificar_modelo.py": {
        "objetivo": "Clasificar temáticamente las preguntas del examen modelo.",
        "entradas": ["Preguntas MODELO pendientes.", "Temario de la convocatoria."],
        "salidas": ["Clasificación guardada o mostrada en modo prueba."],
        "flujo": ["Carga preguntas.", "Ejecuta el clasificador.", "Aplica correcciones.", "Guarda resultados."],
    },
    "procesos/clasificar_pendientes.py": {
        "objetivo": "Clasificar en lote preguntas pendientes de validación.",
        "entradas": ["Preguntas pendientes.", "Temario de la convocatoria."],
        "salidas": ["Estados y clasificación temática actualizados."],
        "flujo": ["Carga pendientes.", "Clasifica.", "Muestra resultados.", "Guarda opcionalmente."],
    },
    "procesos/clasificar_pregunta.py": {
        "objetivo": "Clasificar y auditar una pregunta concreta.",
        "entradas": ["Identificador de pregunta importada."],
        "salidas": ["Diagnóstico y clasificación de la pregunta."],
        "flujo": ["Carga la pregunta.", "Ejecuta el clasificador.", "Muestra o guarda el resultado."],
    },
    "procesos/clasificar_tipo_pregunta.py": {
        "objetivo": "Asignar GENERAL, ESPECIAL_TEORIA, ESPECIAL_PRACTICA o ESPECIAL_INFORMATICA.",
        "entradas": ["Preguntas validadas sin tipo."],
        "salidas": ["Tipo de pregunta actualizado."],
        "flujo": ["Carga pendientes.", "Analiza parte y redacción.", "Asigna el tipo definitivo."],
    },
    "procesos/completar_simulacro_ia.py": {
        "objetivo": "Completar mediante IA los huecos de un simulacro no cubiertos por el banco.",
        "entradas": ["Simulacro incompleto.", "Documentación del tema."],
        "salidas": ["Simulacro completo en JSON."],
        "flujo": ["Detecta faltantes.", "Construye prompts.", "Genera preguntas.", "Valida y ordena."],
    },
    "procesos/documentar_scripts.py": {
        "objetivo": "Auditar, normalizar y documentar los scripts Python del proyecto.",
        "entradas": ["Scripts Python de core, procesos y render."],
        "salidas": ["Cabeceras, inventario e informe de auditoría."],
        "flujo": ["Analiza scripts.", "Actualiza cabeceras.", "Audita.", "Genera documentación."],
    },
    "procesos/exportar_simulacro_html.py": {
        "objetivo": "Exportar un simulacro JSON a HTML imprimible.",
        "entradas": ["Simulacro JSON."],
        "salidas": ["HTML del examen y soluciones."],
        "flujo": ["Carga el JSON.", "Compone preguntas.", "Añade soluciones.", "Guarda HTML."],
    },
    "procesos/extraer_pdf_imagenes.py": {
        "objetivo": "Extraer preguntas desde un PDF compuesto por imágenes.",
        "entradas": ["PDF con una pregunta por página."],
        "salidas": ["JSON con preguntas extraídas e incidencias."],
        "flujo": ["Renderiza páginas.", "Envía imágenes a OpenAI.", "Valida estructura.", "Guarda JSON."],
    },
    "procesos/generar_explicaciones.py": {
        "objetivo": "Añadir explicaciones justificadas a un simulacro.",
        "entradas": ["Simulacro completo.", "Fragmentos normativos."],
        "salidas": ["Simulacro explicado en JSON y explicaciones reutilizables."],
        "flujo": ["Busca explicaciones existentes.", "Recupera fragmentos.", "Genera faltantes.", "Guarda."],
    },
    "procesos/generar_pdf.py": {
        "objetivo": "Generar los PDF de examen y soluciones de un simulacro.",
        "entradas": ["Simulacro explicado en JSON."],
        "salidas": ["PDF del examen y PDF de soluciones."],
        "flujo": ["Carga el simulacro.", "Normaliza.", "Genera ambos PDF."],
    },
    "procesos/generar_simulacro.py": {
        "objetivo": "Generar y guardar un simulacro desde el banco de preguntas.",
        "entradas": ["Distribución oficial.", "Banco de la convocatoria."],
        "salidas": ["Simulacro JSON y resumen de faltantes."],
        "flujo": ["Construye el simulacro.", "Ordena preguntas.", "Guarda JSON.", "Muestra resumen."],
    },
    "procesos/importar_json_extraido.py": {
        "objetivo": "Incorporar a la convocatoria preguntas extraídas desde PDF de imágenes.",
        "entradas": ["JSON extraído.", "PDF de origen.", "Código CFG."],
        "salidas": ["Examen, preguntas y opciones importadas; informe de incidencias."],
        "flujo": ["Valida estructura.", "Elimina duplicados.", "Valida por pie.", "Inserta en SQLite."],
    },
    "procesos/normalizar_cabeceras.py": {
        "objetivo": "Auditar el cumplimiento de la cabecera estándar en los scripts.",
        "entradas": ["Scripts Python del proyecto."],
        "salidas": ["docs/CABECERAS_PENDIENTES.md."],
        "flujo": ["Lee docstrings.", "Comprueba campos.", "Genera informe."],
    },
}


def crear_argumentos():
    parser = argparse.ArgumentParser(
        description="Audita, normaliza y documenta scripts Python."
    )
    parser.add_argument(
        "--actualizar-cabeceras",
        action="store_true",
        help="Sustituye las cabeceras y crea copia de seguridad.",
    )
    parser.add_argument(
        "--solo-auditar",
        action="store_true",
        help="Genera únicamente la auditoría.",
    )
    parser.add_argument(
        "--solo-documentacion",
        action="store_true",
        help="Genera únicamente el inventario.",
    )
    return parser.parse_args()


def ruta_relativa(ruta):
    return str(ruta.relative_to(ROOT)).replace("\\", "/")


def modulo_desde_ruta(ruta):
    partes = list(ruta.relative_to(ROOT).with_suffix("").parts)
    if partes and partes[-1] == "__init__":
        partes = partes[:-1]
    return ".".join(partes)


def obtener_scripts():
    scripts = []
    for carpeta in CARPETAS_CODIGO:
        if not carpeta.exists():
            continue
        for ruta in carpeta.rglob("*.py"):
            if "__pycache__" not in ruta.parts:
                scripts.append(ruta)
    return sorted(scripts, key=lambda ruta: ruta_relativa(ruta).lower())


def leer_texto(ruta):
    return ruta.read_text(encoding="utf-8-sig")


def extraer_docstring(arbol):
    return ast.get_docstring(arbol, clean=False) or ""


def obtener_imports(arbol):
    imports = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name.startswith(("core", "procesos", "render")):
                    imports.add(alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module and nodo.module.startswith(("core", "procesos", "render")):
                imports.add(nodo.module)
    return sorted(imports)


def tiene_main(arbol):
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.If):
            continue
        try:
            texto = ast.unparse(nodo.test)
        except Exception:
            continue
        if "__name__" in texto and "__main__" in texto:
            return True
    return False


def detectar_escritura_bd(texto):
    mayusculas = texto.upper()
    return any(palabra in mayusculas for palabra in PALABRAS_SQL_ESCRITURA)


def detectar_tablas(texto):
    patrones = (
        r"\bINSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bUPDATE\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bDELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bCREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bALTER\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bDROP\s+TABLE(?:\s+IF\s+EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)",
    )
    tablas = set()
    for patron in patrones:
        tablas.update(
            coincidencia.lower()
            for coincidencia in re.findall(patron, texto, flags=re.IGNORECASE)
            if coincidencia.lower() not in {"set"}
        )
    return sorted(tablas)


def inferir_tipo(ruta):
    relativa = ruta_relativa(ruta)
    if relativa.startswith("core/"):
        return "Core"
    if relativa.startswith("procesos/"):
        return "Proceso"
    return "Utilidad"


def analizar_script(ruta):
    texto = leer_texto(ruta)
    try:
        arbol = ast.parse(texto)
    except SyntaxError as error:
        return {
            "ruta": ruta_relativa(ruta),
            "modulo": modulo_desde_ruta(ruta),
            "error": f"Línea {error.lineno}: {error.msg}",
        }

    return {
        "ruta": ruta_relativa(ruta),
        "modulo": modulo_desde_ruta(ruta),
        "docstring": extraer_docstring(arbol),
        "tipo": inferir_tipo(ruta),
        "estado": "OK",
        "imports": obtener_imports(arbol),
        "utilizado_por": [],
        "tiene_main": tiene_main(arbol),
        "modifica_bd": "Sí" if detectar_escritura_bd(texto) else "No",
        "tablas": detectar_tablas(texto),
        "texto": texto,
        "arbol": arbol,
        "error": None,
    }


def relacionar_dependencias(resultados):
    por_modulo = {
        resultado["modulo"]: resultado
        for resultado in resultados
        if not resultado["error"] and resultado["modulo"]
    }
    usados = defaultdict(set)

    for resultado in resultados:
        if resultado["error"]:
            continue
        for importado in resultado["imports"]:
            for modulo in por_modulo:
                if importado == modulo or importado.startswith(modulo + "."):
                    if modulo != resultado["modulo"]:
                        usados[modulo].add(resultado["ruta"])

    for resultado in resultados:
        resultado["utilizado_por"] = sorted(usados.get(resultado["modulo"], set()))

    return resultados


def lineas_lista(valores, vacio="- Ninguna."):
    if not valores:
        return [f"    {vacio}"]
    return [f"    - {valor}" for valor in valores]


def construir_cabecera(resultado):
    ruta = resultado["ruta"]
    metadata = METADATOS.get(
        ruta,
        {
            "objetivo": "Proporcionar funcionalidad auxiliar al proyecto.",
            "entradas": ["Datos propios del módulo."],
            "salidas": ["Resultado propio del módulo."],
            "flujo": ["Recibe los datos.", "Procesa la información.", "Devuelve el resultado."],
        },
    )

    utiliza = resultado["imports"]
    utilizado_por = resultado["utilizado_por"]
    tablas = resultado["tablas"]

    lineas = [
        '"""',
        "==============================================================================",
        "Proyecto : OpoCoach",
        f"Tipo     : {resultado['tipo']}",
        "Estado   : OK",
        "",
        f"Archivo : {Path(ruta).name}",
        f"Ruta    : {ruta}",
        "",
        "Objetivo:",
        f"    {metadata['objetivo']}",
        "",
        "Entradas:",
        *lineas_lista(metadata.get("entradas", [])),
        "",
        "Salidas:",
        *lineas_lista(metadata.get("salidas", [])),
        "",
        "Modifica BD:",
        f"    {resultado['modifica_bd']}",
        "",
        "Tablas afectadas:",
        *lineas_lista(tablas),
        "",
        "Utiliza:",
        *lineas_lista(utiliza),
        "",
        "Utilizado por:",
        *lineas_lista(utilizado_por),
        "",
        "Flujo:",
    ]

    for indice, paso in enumerate(metadata.get("flujo", []), start=1):
        lineas.append(f"    {indice}. {paso}")

    lineas.extend(
        [
            "",
            "Observaciones:",
            "    - Ninguna.",
            "",
            "==============================================================================",
            '"""',
            "",
        ]
    )

    return "\n".join(lineas)


def quitar_docstring_inicial(texto):
    try:
        arbol = ast.parse(texto)
    except SyntaxError:
        return texto

    if not arbol.body:
        return texto

    primero = arbol.body[0]

    if not (
        isinstance(primero, ast.Expr)
        and isinstance(primero.value, ast.Constant)
        and isinstance(primero.value.value, str)
    ):
        return texto.lstrip("\ufeff")

    lineas = texto.splitlines(keepends=True)
    inicio = primero.lineno - 1
    fin = primero.end_lineno

    return "".join(lineas[:inicio] + lineas[fin:]).lstrip("\r\n")


def crear_backup(resultados):
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = RUTA_BACKUPS / marca

    for resultado in resultados:
        if resultado["error"] or resultado["ruta"].endswith("__init__.py"):
            continue

        origen = ROOT / resultado["ruta"]
        destino = carpeta / resultado["ruta"]
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)

    return carpeta


def actualizar_cabeceras(resultados):
    carpeta_backup = crear_backup(resultados)
    modificados = 0

    for resultado in resultados:
        if resultado["error"] or resultado["ruta"].endswith("__init__.py"):
            continue

        ruta = ROOT / resultado["ruta"]
        cuerpo = quitar_docstring_inicial(resultado["texto"])
        nuevo = construir_cabecera(resultado) + cuerpo.lstrip()
        ruta.write_text(nuevo, encoding="utf-8")
        modificados += 1

    return modificados, carpeta_backup


def extraer_campo_linea(docstring, campo):
    coincidencia = re.search(
        rf"(?mi)^\s*{re.escape(campo)}\s*:\s*(.*?)\s*$",
        docstring,
    )
    return coincidencia.group(1).strip() if coincidencia else None


def contiene_campo(docstring, campo):
    return re.search(
        rf"(?mi)^\s*{re.escape(campo)}\s*:",
        docstring,
    ) is not None


def auditar_cabecera(resultado):
    if resultado["error"]:
        return ["Error de sintaxis: " + resultado["error"]]

    if resultado["ruta"].endswith("__init__.py") and not resultado["docstring"]:
        return []

    if not resultado["docstring"]:
        return ["El archivo no contiene docstring inicial."]

    incidencias = [
        f"Falta el campo: {campo}."
        for campo in CAMPOS_OBLIGATORIOS
        if not contiene_campo(resultado["docstring"], campo)
    ]

    proyecto = extraer_campo_linea(resultado["docstring"], "Proyecto")
    if proyecto is not None and proyecto != "OpoCoach":
        incidencias.append("Proyecto debe ser OpoCoach.")

    tipo = extraer_campo_linea(resultado["docstring"], "Tipo")
    if tipo is not None and tipo not in TIPOS_VALIDOS:
        incidencias.append(f"Tipo no válido: {tipo!r}.")

    estado = extraer_campo_linea(resultado["docstring"], "Estado")
    if estado is not None and estado not in ESTADOS_VALIDOS:
        incidencias.append(f"Estado no válido: {estado!r}.")

    archivo = extraer_campo_linea(resultado["docstring"], "Archivo")
    if archivo is not None and archivo != Path(resultado["ruta"]).name:
        incidencias.append("El campo Archivo no coincide con el nombre real.")

    ruta_cabecera = extraer_campo_linea(resultado["docstring"], "Ruta")
    if ruta_cabecera is not None and ruta_cabecera.replace("\\", "/") != resultado["ruta"]:
        incidencias.append("El campo Ruta no coincide con la ruta real.")

    return incidencias


def generar_informe_cabeceras(resultados):
    RUTA_CABECERAS.parent.mkdir(parents=True, exist_ok=True)
    grupos = defaultdict(list)

    for resultado in resultados:
        incidencias = auditar_cabecera(resultado)
        if resultado["error"]:
            estado = "ERROR_SINTAXIS"
        elif incidencias:
            estado = (
                "SIN_CABECERA"
                if any("no contiene docstring" in x for x in incidencias)
                else "INCOMPLETA"
            )
        else:
            estado = "CORRECTA"
        grupos[estado].append((resultado, incidencias))

    lineas = [
        "# OpoCoach",
        "",
        "**Documento:** Auditoría de cabeceras",
        "",
        "## Resumen",
        "",
        "| Estado | Cantidad |",
        "|---|---:|",
        f"| Correctas | {len(grupos['CORRECTA'])} |",
        f"| Incompletas | {len(grupos['INCOMPLETA'])} |",
        f"| Sin cabecera | {len(grupos['SIN_CABECERA'])} |",
        f"| Error de sintaxis | {len(grupos['ERROR_SINTAXIS'])} |",
        f"| Total | {len(resultados)} |",
        "",
    ]

    for clave, titulo in (
        ("INCOMPLETA", "Cabeceras incompletas"),
        ("SIN_CABECERA", "Archivos sin cabecera"),
        ("ERROR_SINTAXIS", "Errores de sintaxis"),
        ("CORRECTA", "Cabeceras correctas"),
    ):
        if not grupos[clave]:
            continue

        lineas.extend([f"## {titulo}", ""])

        for resultado, incidencias in grupos[clave]:
            if clave == "CORRECTA":
                lineas.append(f"- `{resultado['ruta']}`")
            else:
                lineas.extend([f"### `{resultado['ruta']}`", ""])
                lineas.extend(f"- {incidencia}" for incidencia in incidencias)
                lineas.append("")

        lineas.append("")

    RUTA_CABECERAS.write_text(
        "\n".join(lineas).rstrip() + "\n",
        encoding="utf-8",
    )
    return grupos


def formato_lista(valores):
    return "—" if not valores else "<br>".join(f"`{valor}`" for valor in valores)


def generar_documentacion(resultados):
    RUTA_SCRIPTS.parent.mkdir(parents=True, exist_ok=True)
    validos = [
        resultado
        for resultado in resultados
        if not resultado["error"] and not resultado["ruta"].endswith("__init__.py")
    ]
    grupos = defaultdict(list)

    for resultado in validos:
        grupos[resultado["tipo"]].append(resultado)

    lineas = [
        "# OpoCoach",
        "",
        "**Versión:** 0.2",
        "",
        "**Documento:** Inventario de scripts",
        "",
        "Generado automáticamente por `procesos/documentar_scripts.py`.",
        "",
    ]

    for tipo in ("Core", "Proceso", "Utilidad"):
        elementos = sorted(grupos.get(tipo, []), key=lambda x: x["ruta"].lower())
        if not elementos:
            continue

        lineas.extend(
            [
                f"## {tipo}",
                "",
                "| Script | Objetivo | BD | Estado | Utilizado por |",
                "|---|---|:---:|:---:|---|",
            ]
        )

        for resultado in elementos:
            metadata = METADATOS.get(resultado["ruta"], {})
            objetivo = metadata.get(
                "objetivo",
                "Proporcionar funcionalidad auxiliar al proyecto.",
            ).replace("|", "\\|")

            lineas.append(
                f"| `{resultado['ruta']}` "
                f"| {objetivo} "
                f"| {resultado['modifica_bd']} "
                f"| OK "
                f"| {formato_lista(resultado['utilizado_por'])} |"
            )

        lineas.append("")

    RUTA_SCRIPTS.write_text(
        "\n".join(lineas).rstrip() + "\n",
        encoding="utf-8",
    )


def main():
    argumentos = crear_argumentos()

    if argumentos.solo_auditar and argumentos.solo_documentacion:
        raise ValueError(
            "No pueden combinarse --solo-auditar y --solo-documentacion."
        )

    resultados = relacionar_dependencias(
        [analizar_script(ruta) for ruta in obtener_scripts()]
    )

    if argumentos.actualizar_cabeceras:
        modificados, backup = actualizar_cabeceras(resultados)
        print(f"Cabeceras actualizadas: {modificados}")
        print(f"Copia de seguridad....: {backup}")

        resultados = relacionar_dependencias(
            [analizar_script(ruta) for ruta in obtener_scripts()]
        )

    grupos = None

    if not argumentos.solo_documentacion:
        grupos = generar_informe_cabeceras(resultados)

    if not argumentos.solo_auditar:
        generar_documentacion(resultados)

    resumen = Counter(
        "ERROR" if resultado["error"] else resultado["tipo"]
        for resultado in resultados
    )

    print()
    print("=" * 70)
    print("DOCUMENTACIÓN DE SCRIPTS")
    print("=" * 70)
    print(f"Scripts...........: {len(resultados)}")
    print(f"Core..............: {resumen['Core']}")
    print(f"Procesos..........: {resumen['Proceso']}")
    print(f"Utilidades........: {resumen['Utilidad']}")
    print(f"Errores sintaxis..: {resumen['ERROR']}")

    if grupos is not None:
        pendientes = len(grupos["INCOMPLETA"]) + len(grupos["SIN_CABECERA"])
        print(f"Cabeceras correctas: {len(grupos['CORRECTA'])}")
        print(f"Cabeceras pendientes: {pendientes}")

    if not argumentos.solo_auditar:
        print(f"Inventario........: {RUTA_SCRIPTS}")

    if not argumentos.solo_documentacion:
        print(f"Auditoría.........: {RUTA_CABECERAS}")


if __name__ == "__main__":
    main()