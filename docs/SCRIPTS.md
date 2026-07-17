# SCRIPTS

## Objetivo

Inventario de los scripts de apoyo y mantenimiento del proyecto.

---

# Importación

Scripts destinados a incorporar información al sistema.

- Importación del temario.
- Importación de documentos.
- Importación de preguntas de exámenes.
- Importación de preguntas generadas.

---

# Procesamiento documental

Scripts relacionados con el corpus documental.

- Fragmentación.
- Indexación.
- Reconstrucción de índices.
- Auditorías documentales.

---

# Validación

Scripts encargados de comprobar la validez de las preguntas respecto a una convocatoria.

- Validación.
- Reclasificación.
- Actualización del banco.

---

# Generación

Procesos que utilizan IA para generar contenido.

- Generación de preguntas.
- Generación de factores de calidad.
- Generación de informes.

---

# Auditoría

Scripts destinados a verificar la consistencia del sistema.

- Integridad de la base de datos.
- Detección de duplicados.
- Verificación del banco.
- Comprobación de documentación.

---

# Mantenimiento

Operaciones periódicas.

- Reimportaciones idempotentes.
- Reconstrucción de índices.
- Reclasificación.
- Limpieza de datos temporales.

---

# Criterios

- Todos los scripts deberán ser idempotentes siempre que sea posible.
- Cada script deberá realizar una única tarea.
- Los scripts de mantenimiento nunca modificarán información sin dejar trazabilidad.