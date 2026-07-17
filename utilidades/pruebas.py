pregunta = datos["preguntas"][0]

pregunta_id = insertar_pregunta(
    conn=conn,
    examen_id=examen_id,
    pregunta=pregunta,
)

insertar_opciones(
    conn=conn,
    pregunta_id=pregunta_id,
    opciones=pregunta["opciones"],
)

insertar_explicacion(
    conn=conn,
    pregunta_id=pregunta_id,
    pregunta=pregunta,
)

conn.commit()

print(
    f"Pregunta ID......: {pregunta_id}"
)