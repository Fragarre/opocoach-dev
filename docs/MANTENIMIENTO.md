# MANTENIMIENTO

## Objetivo

Describir los procesos de mantenimiento necesarios para conservar la coherencia del sistema.

---

# Principios

- Todos los procesos deberán ser idempotentes siempre que sea posible.
- Ningún proceso modificará información sin dejar trazabilidad.
- El mantenimiento deberá poder ejecutarse de forma independiente.

---

# Importaciones

Procesos destinados a incorporar información al sistema.

- Temario.
- Documentación.
- Preguntas de exámenes.
- Preguntas generadas.

Las importaciones deberán poder repetirse sin producir duplicados.

---

# Banco de preguntas

Operaciones de mantenimiento:

- validación;
- reclasificación;
- incorporación;
- eliminación de duplicados.

---

# Cambios en el temario

Cuando cambie el temario de una convocatoria será necesario:

1. Actualizar el temario.
2. Revisar la clasificación afectada.
3. Revalidar las preguntas.
4. Actualizar el banco.

No será necesario reimportar las preguntas originales.

---

# Auditorías

El sistema deberá disponer de procesos para verificar:

- integridad documental;
- coherencia del banco;
- preguntas duplicadas;
- referencias normativas;
- índices de búsqueda.

---

# Índices

Los índices de búsqueda podrán reconstruirse cuando sea necesario sin afectar a la información almacenada.

---

# Copias de seguridad

Antes de ejecutar procesos masivos que modifiquen datos deberá existir una copia de seguridad de la base de datos.