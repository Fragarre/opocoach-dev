# ARQUITECTURA

## Objetivo

Describir la arquitectura funcional de OpoCoach y las relaciones entre sus principales componentes.

---

# Arquitectura general

```text
Convocatoria
      │
      ▼
 Temario oficial
      │
      ▼
Corpus documental
      │
      ▼
Fragmentación
      │
      ▼
Índice de búsqueda
      │
      ▼
Generación / Importación
      │
      ▼
Validación
      │
      ▼
Clasificación
      │
      ▼
Banco de preguntas
      │
      ▼
Simulacros
      │
      ▼
Corrección
      │
      ▼
Informe IA
```

---

# Convocatoria

Cada convocatoria define:

- temario;
- distribución del examen;
- configuración de generación;
- banco de preguntas.

Las convocatorias son independientes entre sí.

---

# Corpus documental

El conocimiento del sistema procede exclusivamente de la documentación oficial asociada al temario.

Los documentos se fragmentan e indexan para permitir su búsqueda.

---

# Preguntas importadas

Las preguntas importadas conservan únicamente su información objetiva:

- examen de procedencia;
- enunciado;
- opciones;
- respuesta oficial;
- norma y artículo de origen.

No almacenan información específica de ninguna convocatoria.

---

# Banco de preguntas

El banco pertenece a una convocatoria.

Cada pregunta del banco contiene únicamente la información necesaria para participar en los procesos de generación de simulacros.

Una misma pregunta importada puede incorporarse a distintos bancos tras superar el proceso de validación correspondiente.

---

# Inteligencia Artificial

La IA interviene únicamente en aquellos procesos donde aporta valor:

- generación;
- validación;
- clasificación;
- informes.

Todo el acceso a IA se realiza mediante el módulo común.

---

# Principios

- Separación entre conocimiento y convocatoria.
- Procesos independientes y reutilizables.
- Arquitectura modular.
- Mínimo acoplamiento entre componentes.
- Una única fuente de verdad para cada dato.