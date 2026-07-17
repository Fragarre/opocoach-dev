from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont

import csv
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import img2pdf
import numpy as np
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_ORIGEN = Path(
    r"C:\Users\fraga\OneDrive\Documentos\marta\opoNew\capturas\capturas_test"
)

CARPETA_SALIDA = CARPETA_ORIGEN.parent / "resultado_test"

CARPETA_LIMPIAS = CARPETA_SALIDA / "capturas_test_limpias"

PDF_TEST = CARPETA_SALIDA / "TEST_SIN_RESPUESTAS.pdf"

PDF_RESPUESTAS = CARPETA_SALIDA / "PLANTILLA_RESPUESTAS.pdf"

CSV_RESPUESTAS = CARPETA_SALIDA / "PLANTILLA_RESPUESTAS.csv"

CSV_REVISION = CARPETA_SALIDA / "REVISION_DETECCION.csv"

# Si es True, borra previamente las salidas anteriores.
RECREAR_SALIDA = True

# Colores HSV aproximados del verde de las respuestas.
# El intervalo es deliberadamente amplio para soportar variaciones JPEG.
HSV_VERDE_MIN = np.array([35, 35, 80], dtype=np.uint8)
HSV_VERDE_MAX = np.array([95, 255, 255], dtype=np.uint8)


# ============================================================
# MODELO DE RESULTADO
# ============================================================

@dataclass
class Resultado:
    numero: int
    archivo: Path
    respuesta: str | None
    confianza: float
    estado: str
    caja_verde: tuple[int, int, int, int] | None


# ============================================================
# UTILIDADES
# ============================================================

def numero_desde_nombre(ruta: Path) -> int:
    """
    Obtiene el número de pregunta desde nombres como 0001.jpg.
    """
    if ruta.stem.isdigit():
        return int(ruta.stem)

    raise ValueError(
        f"El archivo no tiene un nombre numérico válido: {ruta.name}"
    )


def listar_imagenes(carpeta: Path) -> list[Path]:
    """
    Lista JPG/JPEG/PNG y los ordena numéricamente.
    """
    extensiones = {".jpg", ".jpeg", ".png"}

    rutas = [
        ruta
        for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in extensiones
    ]

    rutas.sort(key=numero_desde_nombre)

    return rutas


def preparar_carpetas() -> None:
    if not CARPETA_ORIGEN.is_dir():
        raise FileNotFoundError(
            f"No existe la carpeta de capturas:\n{CARPETA_ORIGEN}"
        )

    if RECREAR_SALIDA and CARPETA_SALIDA.exists():
        shutil.rmtree(CARPETA_SALIDA)

    CARPETA_LIMPIAS.mkdir(parents=True, exist_ok=True)


# ============================================================
# DETECCIÓN DEL RECUADRO VERDE
# ============================================================

def detectar_caja_verde(
    imagen_bgr: np.ndarray,
) -> tuple[tuple[int, int, int, int] | None, float]:
    """
    Detecta el recuadro verde de la respuesta correcta.

    Devuelve:
        ((x, y, ancho, alto), confianza)

    La búsqueda se limita principalmente al lado izquierdo,
    donde están las letras A-D.
    """
    alto, ancho = imagen_bgr.shape[:2]

    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)

    mascara = cv2.inRange(hsv, HSV_VERDE_MIN, HSV_VERDE_MAX)

    # Solo buscamos en la zona donde aparecen las casillas A-D.
    limite_x = int(ancho * 0.28)

    mascara[:, limite_x:] = 0

    # Elimina ruido pequeño y agrupa la zona verde principal.
    kernel = np.ones((5, 5), np.uint8)

    mascara = cv2.morphologyEx(
        mascara,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1,
    )

    mascara = cv2.morphologyEx(
        mascara,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    contornos, _ = cv2.findContours(
        mascara,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidatos: list[tuple[float, tuple[int, int, int, int]]] = []

    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)

        area = w * h

        if area < 400:
            continue

        relacion = w / max(h, 1)

        # Las cajas son aproximadamente cuadradas o ligeramente rectangulares.
        if not 0.45 <= relacion <= 1.8:
            continue

        # Descarta objetos demasiado grandes.
        if w > ancho * 0.12 or h > alto * 0.20:
            continue

        # Descarta objetos demasiado pequeños.
        if w < ancho * 0.012 or h < alto * 0.025:
            continue

        region = mascara[y : y + h, x : x + w]

        proporcion_verde = cv2.countNonZero(region) / float(area)

        # La casilla verde debe tener una proporción relevante de verde.
        if proporcion_verde < 0.25:
            continue

        # Preferimos cajas compactas y suficientemente verdes.
        puntuacion = area * proporcion_verde

        candidatos.append((puntuacion, (x, y, w, h)))

    if not candidatos:
        return None, 0.0

    candidatos.sort(key=lambda elemento: elemento[0], reverse=True)

    puntuacion, caja = candidatos[0]

    x, y, w, h = caja

    region = mascara[y : y + h, x : x + w]

    proporcion_verde = cv2.countNonZero(region) / float(w * h)

    confianza = min(1.0, max(0.0, proporcion_verde))

    return caja, confianza


# ============================================================
# DETECCIÓN DE LAS CUATRO CASILLAS
# ============================================================

def detectar_cajas_respuesta(
    imagen_bgr: np.ndarray,
) -> list[tuple[int, int, int, int]]:
    """
    Busca las cajas A-D en la franja izquierda.

    Se usan bordes y geometría para encontrar tanto las cajas
    blancas como la caja verde.
    """
    alto, ancho = imagen_bgr.shape[:2]

    limite_x = int(ancho * 0.28)

    zona = imagen_bgr[:, :limite_x]

    gris = cv2.cvtColor(zona, cv2.COLOR_BGR2GRAY)

    gris = cv2.GaussianBlur(gris, (5, 5), 0)

    bordes = cv2.Canny(gris, 25, 90)

    kernel = np.ones((3, 3), np.uint8)

    bordes = cv2.dilate(bordes, kernel, iterations=1)

    contornos, _ = cv2.findContours(
        bordes,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidatos: list[tuple[int, int, int, int]] = []

    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)

        relacion = w / max(h, 1)

        if not 0.45 <= relacion <= 1.65:
            continue

        if not ancho * 0.012 <= w <= ancho * 0.10:
            continue

        if not alto * 0.025 <= h <= alto * 0.18:
            continue

        if x > ancho * 0.20:
            continue

        candidatos.append((x, y, w, h))

    # Elimina cajas duplicadas producidas por borde interior y exterior.
    candidatos.sort(key=lambda caja: (caja[1], caja[0]))

    depurados: list[tuple[int, int, int, int]] = []

    for candidato in candidatos:
        x, y, w, h = candidato

        centro_y = y + h / 2

        duplicado = False

        for existente in depurados:
            ex, ey, ew, eh = existente

            centro_existente = ey + eh / 2

            if abs(centro_y - centro_existente) < max(h, eh) * 0.45:
                duplicado = True
                break

        if not duplicado:
            depurados.append(candidato)

    return depurados


def identificar_respuesta(
    imagen_bgr: np.ndarray,
    caja_verde: tuple[int, int, int, int],
) -> tuple[str | None, float]:
    """
    Identifica A, B, C o D comparando la posición vertical
    de la caja verde con las cajas de respuesta detectadas.
    """
    cajas = detectar_cajas_respuesta(imagen_bgr)

    vx, vy, vw, vh = caja_verde

    centro_verde = vy + vh / 2

    # Conservamos las cajas razonablemente próximas en X
    # a la caja verde.
    cajas_compatibles = []

    for caja in cajas:
        x, y, w, h = caja

        centro_x = x + w / 2
        centro_verde_x = vx + vw / 2

        if abs(centro_x - centro_verde_x) <= max(vw, w) * 1.7:
            cajas_compatibles.append(caja)

    cajas_compatibles.sort(key=lambda caja: caja[1] + caja[3] / 2)

    # Si detectamos al menos cuatro filas, escogemos las cuatro
    # que mejor rodean a la caja verde.
    if len(cajas_compatibles) >= 4:
        centros = [
            caja[1] + caja[3] / 2
            for caja in cajas_compatibles
        ]

        indice_mas_cercano = min(
            range(len(centros)),
            key=lambda i: abs(centros[i] - centro_verde),
        )

        inicio = max(0, min(indice_mas_cercano - 1, len(centros) - 4))

        grupo = cajas_compatibles[inicio : inicio + 4]

        centros_grupo = [
            caja[1] + caja[3] / 2
            for caja in grupo
        ]

        indice = min(
            range(4),
            key=lambda i: abs(centros_grupo[i] - centro_verde),
        )

        distancia = abs(centros_grupo[indice] - centro_verde)

        altura_media = sum(caja[3] for caja in grupo) / 4

        confianza = max(
            0.0,
            min(1.0, 1.0 - distancia / max(altura_media, 1)),
        )

        return "ABCD"[indice], confianza

    # Método alternativo: estimar las cuatro filas según la posición
    # relativa de la caja verde dentro de la zona de respuestas.
    alto = imagen_bgr.shape[0]

    posicion = centro_verde / alto

    # Intervalos amplios observados en las capturas.
    if posicion < 0.34:
        return "A", 0.55

    if posicion < 0.50:
        return "B", 0.50

    if posicion < 0.67:
        return "C", 0.50

    return "D", 0.55


# ============================================================
# LIMPIEZA DEL VERDE
# ============================================================

def limpiar_recuadro_verde(
    imagen_bgr: np.ndarray,
    caja: tuple[int, int, int, int],
    respuesta: str,
) -> np.ndarray:
    """
    Elimina el fondo verde y reconstruye la casilla como una opción
    normal, conservando claramente la letra A, B, C o D.
    """
    resultado = imagen_bgr.copy()

    x, y, w, h = caja

    # Amplía ligeramente para cubrir toda la casilla.
    margen = max(2, int(min(w, h) * 0.05))

    x1 = max(0, x - margen)
    y1 = max(0, y - margen)
    x2 = min(resultado.shape[1], x + w + margen)
    y2 = min(resultado.shape[0], y + h + margen)

    # Blanco completo en la zona de la casilla.
    resultado[y1:y2, x1:x2] = (255, 255, 255)

    # Pasar a Pillow para dibujar borde y letra con buena calidad.
    imagen_rgb = cv2.cvtColor(resultado, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(imagen_rgb)
    dibujo = ImageDraw.Draw(pil)

    grosor = max(2, int(min(w, h) * 0.025))
    radio = max(4, int(min(w, h) * 0.10))

    # Borde gris similar a las opciones no seleccionadas.
    dibujo.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=radio,
        fill=(255, 255, 255),
        outline=(210, 210, 210),
        width=grosor,
    )

    # Fuente para la letra.
    tam_fuente = max(18, int(h * 0.42))

    posibles_fuentes = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]

    fuente = None

    for ruta_fuente in posibles_fuentes:
        if Path(ruta_fuente).exists():
            fuente = ImageFont.truetype(
                ruta_fuente,
                tam_fuente,
            )
            break

    if fuente is None:
        fuente = ImageFont.load_default()

    # Calcular centrado real de la letra.
    bbox = dibujo.textbbox(
        (0, 0),
        respuesta,
        font=fuente,
    )

    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]

    centro_x = x + w / 2
    centro_y = y + h / 2

    pos_x = centro_x - ancho_texto / 2
    pos_y = centro_y - alto_texto / 2 - bbox[1]

    dibujo.text(
        (pos_x, pos_y),
        respuesta,
        font=fuente,
        fill=(70, 70, 70),
    )

    return cv2.cvtColor(
        np.asarray(pil),
        cv2.COLOR_RGB2BGR,
    )

# ============================================================
# PROCESAMIENTO DE UNA IMAGEN
# ============================================================

def procesar_imagen(ruta: Path) -> Resultado:
    numero = numero_desde_nombre(ruta)

    imagen = cv2.imread(str(ruta), cv2.IMREAD_COLOR)

    if imagen is None:
        return Resultado(
            numero=numero,
            archivo=ruta,
            respuesta=None,
            confianza=0.0,
            estado="ERROR_LECTURA",
            caja_verde=None,
        )

    caja_verde, confianza_verde = detectar_caja_verde(imagen)

    if caja_verde is None:
        return Resultado(
            numero=numero,
            archivo=ruta,
            respuesta=None,
            confianza=0.0,
            estado="NO_SE_DETECTA_VERDE",
            caja_verde=None,
        )

    respuesta, confianza_posicion = identificar_respuesta(
        imagen,
        caja_verde,
    )

    confianza_total = confianza_verde * confianza_posicion

    if respuesta is None:
        return Resultado(
            numero=numero,
            archivo=ruta,
            respuesta=None,
            confianza=confianza_total,
            estado="RESPUESTA_NO_IDENTIFICADA",
            caja_verde=caja_verde,
        )

    limpia = limpiar_recuadro_verde(
    imagen,
    caja_verde,
    respuesta,
    )

    salida = CARPETA_LIMPIAS / ruta.name

    parametros_jpeg = [
        int(cv2.IMWRITE_JPEG_QUALITY),
        90,
        int(cv2.IMWRITE_JPEG_OPTIMIZE),
        1,
    ]

    guardado = cv2.imwrite(
        str(salida),
        limpia,
        parametros_jpeg,
    )

    if not guardado:
        return Resultado(
            numero=numero,
            archivo=ruta,
            respuesta=respuesta,
            confianza=confianza_total,
            estado="ERROR_GUARDADO",
            caja_verde=caja_verde,
        )

    estado = (
        "OK"
        if confianza_total >= 0.45
        else "REVISAR"
    )

    return Resultado(
        numero=numero,
        archivo=ruta,
        respuesta=respuesta,
        confianza=confianza_total,
        estado=estado,
        caja_verde=caja_verde,
    )


# ============================================================
# ARCHIVOS DE RESPUESTAS
# ============================================================

def crear_csv_respuestas(resultados: list[Resultado]) -> None:
    with CSV_RESPUESTAS.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.writer(archivo, delimiter=";")

        escritor.writerow(["Pregunta", "Correcta"])

        for resultado in resultados:
            escritor.writerow([
                resultado.numero,
                resultado.respuesta or "",
            ])


def crear_csv_revision(resultados: list[Resultado]) -> None:
    with CSV_REVISION.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.writer(archivo, delimiter=";")

        escritor.writerow([
            "Pregunta",
            "Archivo",
            "Respuesta_detectada",
            "Confianza",
            "Estado",
            "Caja_x",
            "Caja_y",
            "Caja_ancho",
            "Caja_alto",
        ])

        for resultado in resultados:
            if resultado.caja_verde:
                x, y, w, h = resultado.caja_verde
            else:
                x = y = w = h = ""

            escritor.writerow([
                resultado.numero,
                resultado.archivo.name,
                resultado.respuesta or "",
                f"{resultado.confianza:.3f}",
                resultado.estado,
                x,
                y,
                w,
                h,
            ])


def crear_pdf_respuestas(resultados: list[Resultado]) -> None:
    documento = SimpleDocTemplate(
        str(PDF_RESPUESTAS),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Plantilla de respuestas",
    )

    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph(
            "PLANTILLA DE RESPUESTAS",
            estilos["Title"],
        ),
        Spacer(1, 8 * mm),
    ]

    filas_por_tabla = 40

    for inicio in range(0, len(resultados), filas_por_tabla):
        bloque = resultados[inicio : inicio + filas_por_tabla]

        datos = [["Pregunta", "Correcta"]]

        for resultado in bloque:
            datos.append([
                str(resultado.numero),
                resultado.respuesta or "REVISAR",
            ])

        tabla = Table(
            datos,
            colWidths=[42 * mm, 42 * mm],
            repeatRows=1,
            hAlign="CENTER",
        )

        tabla.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#E8E8E8"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, -1),
                        "Helvetica",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#B0B0B0"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#F7F7F7"),
                        ],
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        elementos.append(tabla)

        if inicio + filas_por_tabla < len(resultados):
            elementos.append(PageBreak())

    documento.build(elementos)


# ============================================================
# CREACIÓN DEL PDF LIMPIO
# ============================================================

def crear_pdf_test() -> None:
    imagenes = listar_imagenes(CARPETA_LIMPIAS)

    if not imagenes:
        raise RuntimeError(
            "No hay capturas limpias para crear el PDF."
        )

    with PDF_TEST.open("wb") as archivo_pdf:
        archivo_pdf.write(
            img2pdf.convert([str(ruta) for ruta in imagenes])
        )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main() -> int:
    try:
        preparar_carpetas()

        imagenes = listar_imagenes(CARPETA_ORIGEN)

        if not imagenes:
            print(
                "No se han encontrado imágenes en:",
                CARPETA_ORIGEN,
            )
            return 1

        print("=" * 70)
        print("PROCESAMIENTO DEL TEST")
        print("=" * 70)
        print(f"Carpeta origen : {CARPETA_ORIGEN}")
        print(f"Imágenes       : {len(imagenes)}")
        print()

        resultados: list[Resultado] = []

        for indice, ruta in enumerate(imagenes, start=1):
            resultado = procesar_imagen(ruta)

            resultados.append(resultado)

            respuesta = resultado.respuesta or "-"

            print(
                f"[{indice:03}/{len(imagenes):03}] "
                f"Pregunta {resultado.numero:03} -> "
                f"{respuesta} | "
                f"{resultado.estado} | "
                f"confianza {resultado.confianza:.2f}"
            )

        crear_csv_respuestas(resultados)
        crear_csv_revision(resultados)
        crear_pdf_respuestas(resultados)
        crear_pdf_test()

        correctas = sum(
            1
            for resultado in resultados
            if resultado.estado == "OK"
        )

        revisar = [
            resultado
            for resultado in resultados
            if resultado.estado != "OK"
        ]

        print()
        print("=" * 70)
        print("PROCESO TERMINADO")
        print("=" * 70)
        print(f"Procesadas correctamente : {correctas}")
        print(f"Pendientes de revisar    : {len(revisar)}")
        print()
        print(f"PDF limpio      : {PDF_TEST}")
        print(f"PDF respuestas  : {PDF_RESPUESTAS}")
        print(f"CSV respuestas  : {CSV_RESPUESTAS}")
        print(f"CSV revisión    : {CSV_REVISION}")
        print(f"JPG limpios     : {CARPETA_LIMPIAS}")

        if revisar:
            print()
            print("Preguntas que conviene revisar:")

            for resultado in revisar:
                print(
                    f"  {resultado.numero}: "
                    f"{resultado.estado} "
                    f"(respuesta={resultado.respuesta or '-'}, "
                    f"confianza={resultado.confianza:.2f})"
                )

        print()
        input("Pulsa Enter para cerrar...")

        return 0

    except Exception as exc:
        print()
        print("ERROR:")
        print(exc)
        print()

        input("Pulsa Enter para cerrar...")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())