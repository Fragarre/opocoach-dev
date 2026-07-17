import io
import os
import numpy as np
import pypdf
from PIL import Image
import cv2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# CONFIGURACIÓN
PDF_ENTRADA = "Ejemplo_1.pdf"
PDF_PREGUNTAS_SALIDA = "Preguntas_Sin_Respuestas.pdf"
PDF_RESPUESTAS_SALIDA = "Respuestas_Solucionario.pdf"

def detectar_y_limpiar_verde(image_bytes, num_pregunta):
    """
    Analiza la imagen de la página para:
    1. Detectar en qué parte vertical está el color verde para saber la respuesta correcta.
    2. Tapar el recuadro verde con blanco para el PDF de preguntas.
    Retorna la imagen limpia (como PIL.Image) y la respuesta estimada (A, B, C, D o un texto).
    """
    # Convertir bytes a imagen de OpenCV (BGR)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, _ = img_bgr.shape
    
    # Convertir a HSV para detectar el color verde con mayor facilidad
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Rango de color verde (ajustable si el tono del PDF varía)
    # El verde menta/claro del PDF suele caer en este rango:
    bajo_verde = np.array([35, 40, 40])
    alto_verde = np.array([85, 255, 255])
    
    mascara_verde = cv2.inRange(img_hsv, bajo_verde, alto_verde)
    
    # Encontrar los contornos de las áreas verdes
    contornos, _ = cv2.findContours(mascara_verde, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    opcion_correcta = "No detectada"
    img_limpia = img_bgr.copy()
    
    if len(contornos) > 0:
        # Tomamos el contorno verde más grande
        c = max(contornos, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(c)
        
        # 1. Tapar el recuadro verde pintándolo de blanco en la imagen limpia
        # Añadimos un pequeño margen para asegurar que se tape por completo
        cv2.rectangle(img_limpia, (x - 2, y - 2), (x + w_box + 2, y + h_box + 2), (255, 255, 255), -1)
        
        # 2. Estimar la opción (A, B, C, D) según su posición vertical relativa en la página
        # Dividimos la altura de la página de manera referencial:
        # Las opciones suelen estar en la mitad inferior de la imagen.
        porcentaje_y = y / h
        if porcentaje_y < 0.45:
            opcion_correcta = "A (o superior)"
        elif porcentaje_y < 0.60:
            opcion_correcta = "B"
        elif porcentaje_y < 0.75:
            opcion_correcta = "C"
        else:
            opcion_correcta = "D"
            
    # Convertir de vuelta la imagen procesada de BGR (OpenCV) a PIL Image
    img_limpia_rgb = cv2.cvtColor(img_limpia, cv2.COLOR_BGR2RGB)
    pil_img_limpia = Image.fromarray(img_limpia_rgb)
    
    return pil_img_limpia, opcion_correcta

def procesar_test():
    print("Iniciando procesamiento de los PDFs...")
    reader = pypdf.PdfReader(PDF_ENTRADA)
    total_paginas = len(reader.pages)
    
    respuestas_lista = []
    imagenes_preguntas = []
    
    # Crear carpeta temporal para almacenar las imágenes procesadas
    os.makedirs("temp_img", exist_ok=True)
    
    for i in range(total_paginas):
        page = reader.pages[i]
        
        # Extraer la primera imagen de la página
        if len(page.images) > 0:
            image_obj = page.images[0]
            image_bytes = image_obj.data
            
            # Limpiar el color verde y obtener la respuesta de la pregunta
            num_pregunta = i + 1
            img_limpia, respuesta = detectar_y_limpiar_verde(image_bytes, num_pregunta)
            
            # Guardar temporalmente la imagen sin respuestas
            ruta_img = f"temp_img/preg_{num_pregunta}.png"
            img_limpia.save(ruta_img, format="PNG")
            imagenes_preguntas.append(ruta_img)
            
            # Guardar la solución en nuestra lista
            respuestas_lista.append((num_pregunta, respuesta))
            print(f"Procesada pregunta {num_pregunta}/{total_paginas} -> Respuesta: {respuesta}")
        else:
            print(f"Advertencia: No se detectó imagen en la página {i+1}")
            
    # --- 1. CONSTRUIR EL PDF DE PREGUNTAS (CONTINUO) ---
    print("\nGenerando PDF de Preguntas Continuas...")
    doc_preguntas = SimpleDocTemplate(
        PDF_PREGUNTAS_SALIDA,
        pagesize=letter,
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    story_preguntas = []
    
    # Ancho máximo para que las imágenes quepan bien en tamaño Letter sin deformarse
    ancho_disponible = letter[0] - 60  
    
    for ruta_img in imagenes_preguntas:
        # Leer dimensiones reales de la imagen para calcular escala proporcional
        with Image.open(ruta_img) as img_ref:
            img_w, img_h = img_ref.size
        
        escala = ancho_disponible / float(img_w)
        nuevo_alto = img_h * escala
        
        # Insertar la imagen en el flujo continuo del PDF
        rl_img = RLImage(ruta_img, width=ancho_disponible, height=nuevo_alto)
        story_preguntas.append(rl_img)
        # Espacio pequeño entre preguntas (así quedan consecutivas en lugar de una por página)
        story_preguntas.append(Spacer(1, 15)) 
        
    doc_preguntas.build(story_preguntas)
    
    # --- 2. CONSTRUIR EL PDF DE RESPUESTAS (CONTINUO) ---
    print("Generando PDF de Respuestas Continuas...")
    doc_respuestas = SimpleDocTemplate(
        PDF_RESPUESTAS_SALIDA,
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    story_respuestas = []
    styles = getSampleStyleSheet()
    
    # Estilos de texto
    estilo_titulo = ParagraphStyle(
        'TituloSoluciones',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20
    )
    estilo_texto = ParagraphStyle(
        'TextoSolucion',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6
    )
    
    story_respuestas.append(Paragraph("<b>SOLUCIONARIO DE PREGUNTAS</b>", estilo_titulo))
    story_respuestas.append(Spacer(1, 10))
    
    # Agrupar las respuestas en un listado continuo
    for num_preg, resp in respuestas_lista:
        texto_linea = f"<b>Pregunta {num_preg:02d}:</b> Opción correcta detectada -> <b>{resp}</b>"
        story_respuestas.append(Paragraph(texto_linea, estilo_texto))
        
    doc_respuestas.build(story_respuestas)
    
    # Limpieza de imágenes temporales
    for ruta_img in imagenes_preguntas:
        try:
            os.remove(ruta_img)
        except OSError:
            pass
    try:
        os.rmdir("temp_img")
    except OSError:
        pass
        
    print(f"\n¡Proceso completado con éxito!")
    print(f"1. Fichero sin respuestas: '{PDF_PREGUNTAS_SALIDA}'")
    print(f"2. Fichero de soluciones: '{PDF_RESPUESTAS_SALIDA}'")

if __name__ == "__main__":
    procesar_test()