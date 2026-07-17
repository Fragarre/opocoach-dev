PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS convocatorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuerpo TEXT NOT NULL,
    numero TEXT NOT NULL,
    anio INTEGER NOT NULL,
    descripcion TEXT,
    codigo_cfg TEXT NOT NULL UNIQUE,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS partes_temario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    convocatoria_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    orden INTEGER NOT NULL,
    FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id) ON DELETE CASCADE,
    UNIQUE (convocatoria_id, nombre)
);

CREATE TABLE IF NOT EXISTS temas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    convocatoria_id INTEGER NOT NULL,
    parte_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id) ON DELETE CASCADE,
    FOREIGN KEY (parte_id) REFERENCES partes_temario(id) ON DELETE CASCADE,
    UNIQUE (parte_id, numero)
);

CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_archivo TEXT NOT NULL,
    tipo_documento TEXT,
    titulo TEXT,
    ruta TEXT NOT NULL,
    hash_archivo TEXT NOT NULL UNIQUE,
    fecha_importacion TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documentos_temas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL,
    tema_id INTEGER NOT NULL,
    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE,
    FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE,
    UNIQUE (documento_id, tema_id)
);

CREATE TABLE IF NOT EXISTS fragmentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL,
    tipo_fragmento TEXT NOT NULL,
    referencia TEXT,
    texto TEXT NOT NULL,
    orden INTEGER NOT NULL,
    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE,
    UNIQUE (documento_id, orden)
);

CREATE TABLE IF NOT EXISTS examenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    convocatoria_id INTEGER NOT NULL,
    tipo_examen TEXT NOT NULL CHECK (tipo_examen IN ('MODELO', 'APOYO')),
    nombre_archivo TEXT NOT NULL,
    ruta TEXT NOT NULL,
    hash_archivo TEXT NOT NULL UNIQUE,
    fecha_importacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preguntas_importadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    examen_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    enunciado TEXT NOT NULL,
    respuesta_correcta TEXT CHECK (respuesta_correcta IN ('A', 'B', 'C', 'D')),
    parte_detectada TEXT,
    tema_detectado INTEGER,
    estado_importacion TEXT NOT NULL DEFAULT 'IMPORTADA'
        CHECK (estado_importacion IN ('IMPORTADA', 'ERROR', 'EXCLUIDA')),
    FOREIGN KEY (examen_id) REFERENCES examenes(id) ON DELETE CASCADE,
    UNIQUE (examen_id, numero)
);

CREATE TABLE IF NOT EXISTS opciones_importadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_importada_id INTEGER NOT NULL,
    letra TEXT NOT NULL CHECK (letra IN ('A', 'B', 'C', 'D')),
    texto TEXT NOT NULL,
    FOREIGN KEY (pregunta_importada_id) REFERENCES preguntas_importadas(id) ON DELETE CASCADE,
    UNIQUE (pregunta_importada_id, letra)
);

CREATE TABLE IF NOT EXISTS banco_preguntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_importada_id INTEGER,
    convocatoria_id INTEGER NOT NULL,
    parte_id INTEGER NOT NULL,
    tema_id INTEGER NOT NULL,
    fragmento_id INTEGER,
    enunciado TEXT NOT NULL,
    respuesta_correcta TEXT NOT NULL CHECK (respuesta_correcta IN ('A', 'B', 'C', 'D')),
    estado TEXT NOT NULL CHECK (estado IN ('VALIDADA', 'A_REVISAR')),
    fecha_alta TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pregunta_importada_id) REFERENCES preguntas_importadas(id) ON DELETE SET NULL,
    FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id) ON DELETE CASCADE,
    FOREIGN KEY (parte_id) REFERENCES partes_temario(id) ON DELETE CASCADE,
    FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE,
    FOREIGN KEY (fragmento_id) REFERENCES fragmentos(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS banco_opciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_pregunta_id INTEGER NOT NULL,
    letra TEXT NOT NULL CHECK (letra IN ('A', 'B', 'C', 'D')),
    texto TEXT NOT NULL,
    FOREIGN KEY (banco_pregunta_id) REFERENCES banco_preguntas(id) ON DELETE CASCADE,
    UNIQUE (banco_pregunta_id, letra)
);

CREATE TABLE IF NOT EXISTS simulacros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    convocatoria_id INTEGER NOT NULL,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    modo TEXT NOT NULL CHECK (modo IN ('PDF', 'INTERACTIVO')),
    estado TEXT NOT NULL DEFAULT 'GENERADO'
        CHECK (estado IN ('GENERADO', 'REALIZADO', 'CORREGIDO')),
    FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulacro_preguntas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacro_id INTEGER NOT NULL,
    banco_pregunta_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    parte_id INTEGER NOT NULL,
    tema_id INTEGER NOT NULL,
    FOREIGN KEY (simulacro_id) REFERENCES simulacros(id) ON DELETE CASCADE,
    FOREIGN KEY (banco_pregunta_id) REFERENCES banco_preguntas(id) ON DELETE CASCADE,
    FOREIGN KEY (parte_id) REFERENCES partes_temario(id) ON DELETE CASCADE,
    FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE CASCADE,
    UNIQUE (simulacro_id, numero)
);

CREATE TABLE IF NOT EXISTS respuestas_simulacro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacro_pregunta_id INTEGER NOT NULL UNIQUE,
    respuesta_usuario TEXT CHECK (respuesta_usuario IN ('A', 'B', 'C', 'D')),
    es_correcta INTEGER CHECK (es_correcta IN (0, 1)),
    FOREIGN KEY (simulacro_pregunta_id) REFERENCES simulacro_preguntas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resultados_simulacro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacro_id INTEGER NOT NULL UNIQUE,
    correctas INTEGER NOT NULL,
    erroneas INTEGER NOT NULL,
    no_contestadas INTEGER NOT NULL,
    puntuacion REAL NOT NULL,
    FOREIGN KEY (simulacro_id) REFERENCES simulacros(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_temas_convocatoria
ON temas(convocatoria_id);

CREATE INDEX IF NOT EXISTS idx_fragmentos_documento
ON fragmentos(documento_id);

CREATE INDEX IF NOT EXISTS idx_preguntas_importadas_examen
ON preguntas_importadas(examen_id);

CREATE INDEX IF NOT EXISTS idx_banco_convocatoria
ON banco_preguntas(convocatoria_id);

CREATE INDEX IF NOT EXISTS idx_banco_tema
ON banco_preguntas(tema_id);

CREATE INDEX IF NOT EXISTS idx_simulacro_preguntas_simulacro
ON simulacro_preguntas(simulacro_id);