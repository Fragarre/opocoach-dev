# ESTRUCTURA DEL PROYECTO

## Objetivo

Describir la organización física del proyecto y la responsabilidad de cada directorio.

---

## Estructura

```text
OpoCoach
│
├── app.py                 Aplicación principal
├── core/                  Funciones comunes
├── procesos/              Procesos funcionales
├── utilidades/            Utilidades compartidas
├── scripts/               Procesos de mantenimiento
├── prompts/               Prompts utilizados por IA
├── datos/                 Archivos de configuración
├── db/                    Base de datos
├── documentos/            Corpus documental
├── logs/                  Registros
├── salida/                Archivos generados
├── docs/                  Documentación
└── tests/                 Pruebas
```

---

## Criterios

- Cada módulo tendrá una única responsabilidad.
- Evitar dependencias innecesarias entre directorios.
- Reutilizar el código común desde `core`.
- Los procesos funcionales se ubicarán en `procesos`.
- Los scripts de mantenimiento se ubicarán en `scripts`.
- Ningún módulo accederá directamente a la IA salvo mediante el módulo común.

---

## Evolución

La incorporación de nuevas funcionalidades deberá respetar esta organización y evitar la creación de estructuras paralelas o duplicadas.