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
    2. Limpiar el verde píxel a píxel conservando el texto oscuro de la letra.
    3. Dibujar un contorno gris para restaurar la casilla vacía idéntica a las demás.
    """
    # Convertir bytes a imagen de OpenCV (BGR)
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, _ = img_bgr.shape
    
    # Convertir a HSV para detectar el color verde con mayor facilidad
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Rango de color verde (ajustable según el tono del PDF)
    bajo_verde = np.array([35, 40, 40])
    alto_verde = np.array([85, 255, 255])
    
    mascara_verde = cv2.inRange(img_hsv, bajo_verde, alto_verde)
    
    # Encontrar los contornos de las áreas verdes
    contornos, _ = cv2.findContours(mascara_verde, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    opcion_correcta = "No detectada"
    img_limpia = img_bgr.copy()
    
    if len(contornos) > 0:
        # Tomamos el contorno verde más grande (la casilla de la respuesta correcta)
        c = max(contornos, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(c)
        
        # 1. Limpieza Inteligente:
        # Reemplazamos los píxeles verdes por blanco, pero conservando los píxeles oscuros (el texto de la letra)
        # Un píxel se considera verde si está en la máscara y no es muy oscuro (brillo > 80 en escala de grises)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        for row in range(y, y + h_box):
            for col in range(x, x + w_box):
                if 0 <= row < h and 0 <= col < w:
                    if mascara_verde[row, col] > 0 and img_gray[row, col] > 80:
                        img_limpia[row, col] = [255, 255, 255] # Lo pintamos de blanco

        # 2. Reconstrucción del recuadro vacío:
        # Dibujamos un contorno rectangular gris fino alrededor de la casilla para que sea idéntica a las demás
        color_borde_gris = (180, 180, 180) # BGR
        cv2.rectangle(img_limpia, (x, y), (x + w_box, y + h_box), color_borde_gris, 1)
        
        # 3. Estimar la opción (A, B, C, D) según su posición vertical relativa en la página
        porcentaje_y = y / h
        if porcentaje_y < 0.45:
            opcion_correcta = "A"
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
        texto_linea = f"<b>Pregunta {num_preg:02d}:</b> Opción correcta -> <b>{resp}</b>"
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