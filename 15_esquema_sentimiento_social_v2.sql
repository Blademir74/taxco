-- ============================================
-- ESQUEMA: SENTIMIENTO SOCIAL Y SATISFACCION CIUDADANA
-- ============================================

SET client_encoding = 'UTF8';

-- ============================================
-- TABLA: fuente_sentimiento
-- ============================================
DROP TABLE IF EXISTS fuente_sentimiento CASCADE;
CREATE TABLE fuente_sentimiento (
    id_fuente SERIAL PRIMARY KEY,
    nombre_fuente VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    peso_confiabilidad NUMERIC(3,2) DEFAULT 1.00,
    CONSTRAINT chk_peso CHECK (peso_confiabilidad BETWEEN 0 AND 1)
);

INSERT INTO fuente_sentimiento (nombre_fuente, descripcion, peso_confiabilidad) VALUES
('Encuesta Casa por Casa', 'Levantamiento directo con ciudadanos', 1.00),
('Foro Ciudadano', 'Participacion en foros municipales', 0.85),
('Redes Sociales', 'Facebook, Twitter/X, WhatsApp', 0.60),
('Denuncias 911', 'Llamadas de emergencia', 0.95),
('Solicitudes Plataforma Municipal', 'Sistema oficial de atencion ciudadana', 0.90),
('Buzon Ciudadano', 'Quejas y sugerencias fisicas', 0.80);

-- ============================================
-- TABLA: categoria_servicio
-- ============================================
DROP TABLE IF EXISTS categoria_servicio CASCADE;
CREATE TABLE categoria_servicio (
    id_categoria SERIAL PRIMARY KEY,
    nombre_categoria VARCHAR(100) NOT NULL UNIQUE,
    pilar_gobierno VARCHAR(50),
    prioridad_estrategica SMALLINT DEFAULT 3,
    CONSTRAINT chk_prioridad CHECK (prioridad_estrategica BETWEEN 1 AND 5)
);

INSERT INTO categoria_servicio (nombre_categoria, pilar_gobierno, prioridad_estrategica) VALUES
('Agua Potable', 'Servicios Publicos', 1),
('Drenaje y Alcantarillado', 'Servicios Publicos', 1),
('Recoleccion de Basura', 'Servicios Publicos', 2),
('Seguridad Publica', 'Seguridad y Justicia', 1),
('Alumbrado Publico', 'Servicios Publicos', 3),
('Bacheo y Pavimentacion', 'Infraestructura', 2),
('Salud y Hospitales', 'Bienestar Social', 1),
('Educacion', 'Bienestar Social', 1),
('Empleo y Economia', 'Desarrollo Economico', 2),
('Transporte Publico', 'Movilidad', 3),
('Parques y Espacios Publicos', 'Desarrollo Urbano', 4),
('Tramites y Gestion Municipal', 'Gobierno', 3);

-- ============================================
-- TABLA: sentimiento_social
-- ============================================
DROP TABLE IF EXISTS sentimiento_social CASCADE;
CREATE TABLE sentimiento_social (
    pk_sentimiento SERIAL PRIMARY KEY,
    pk_seccion INTEGER NOT NULL REFERENCES seccion(pk_seccion) ON DELETE CASCADE,
    id_fuente INTEGER NOT NULL REFERENCES fuente_sentimiento(id_fuente),
    id_categoria INTEGER NOT NULL REFERENCES categoria_servicio(id_categoria),
    
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calificacion SMALLINT NOT NULL,
    sentimiento_polaridad NUMERIC(3,2) NOT NULL,
    comentario TEXT,
    
    respondente_genero CHAR(1),
    respondente_edad_rango VARCHAR(20),
    capturado_por VARCHAR(100),
    validado BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT chk_calificacion CHECK (calificacion BETWEEN 1 AND 5),
    CONSTRAINT chk_polaridad CHECK (sentimiento_polaridad BETWEEN -1 AND 1),
    CONSTRAINT chk_genero CHECK (respondente_genero IN ('M', 'F', 'O', NULL))
);

CREATE INDEX idx_sentimiento_seccion ON sentimiento_social(pk_seccion);
CREATE INDEX idx_sentimiento_fecha ON sentimiento_social(fecha_registro DESC);
CREATE INDEX idx_sentimiento_categoria ON sentimiento_social(id_categoria);
CREATE INDEX idx_sentimiento_fuente ON sentimiento_social(id_fuente);

-- ============================================
-- TABLA: denuncias_ciudadanas
-- ============================================
DROP TABLE IF EXISTS denuncias_ciudadanas CASCADE;
CREATE TABLE denuncias_ciudadanas (
    pk_denuncia SERIAL PRIMARY KEY,
    pk_seccion INTEGER NOT NULL REFERENCES seccion(pk_seccion),
    id_categoria INTEGER NOT NULL REFERENCES categoria_servicio(id_categoria),
    
    fecha_denuncia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    canal_reporte VARCHAR(50),
    descripcion TEXT,
    estatus VARCHAR(30) DEFAULT 'PENDIENTE',
    fecha_resolucion TIMESTAMP,
    tiempo_resolucion_dias INTEGER,
    
    CONSTRAINT chk_estatus CHECK (estatus IN ('PENDIENTE', 'EN_PROCESO', 'RESUELTO', 'CERRADO'))
);

DROP INDEX IF EXISTS idx_denuncias_seccion;
DROP INDEX IF EXISTS idx_denuncias_estatus;
CREATE INDEX idx_denuncias_seccion ON denuncias_ciudadanas(pk_seccion);
CREATE INDEX idx_denuncias_estatus ON denuncias_ciudadanas(estatus);

-- ============================================
-- VISTA: vw_indice_satisfaccion_seccion
-- ============================================
DROP VIEW IF EXISTS vw_indice_satisfaccion_seccion CASCADE;
CREATE VIEW vw_indice_satisfaccion_seccion AS
SELECT 
    s.seccion,
    s.pk_seccion,
    
    ROUND(
        SUM(ss.calificacion * fs.peso_confiabilidad) / 
        NULLIF(SUM(fs.peso_confiabilidad), 0), 
        2
    ) as calificacion_promedio,
    
    ROUND(AVG(ss.sentimiento_polaridad), 2) as sentimiento_promedio,
    
    ROUND(
        (SUM(ss.calificacion * fs.peso_confiabilidad) / 
         NULLIF(SUM(fs.peso_confiabilidad), 0) - 1) * 25, 
        1
    ) as indice_satisfaccion_ciudadana,
    
    COUNT(*) as total_opiniones,
    MAX(ss.fecha_registro) as ultima_actualizacion
    
FROM seccion s
LEFT JOIN sentimiento_social ss ON ss.pk_seccion = s.pk_seccion
LEFT JOIN fuente_sentimiento fs ON fs.id_fuente = ss.id_fuente
WHERE s.id_municipio = 56
GROUP BY s.seccion, s.pk_seccion;

-- ============================================
-- VISTA: vw_riesgo_electoral
-- ============================================
DROP VIEW IF EXISTS vw_riesgo_electoral CASCADE;
CREATE VIEW vw_riesgo_electoral AS
WITH ganadores_2024 AS (
    SELECT 
        c.pk_seccion,
        p.clave_partido,
        SUM(rp.votos) as votos,
        ROW_NUMBER() OVER (PARTITION BY c.pk_seccion ORDER BY SUM(rp.votos) DESC) as rn
    FROM casilla c
    JOIN eleccion e ON e.id_eleccion = c.id_eleccion
    JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
    JOIN resultados_partido rp ON rp.pk_resultado = re.pk_resultado
    JOIN partido p ON p.id_partido = rp.id_partido
    WHERE e.anio = 2024
    GROUP BY c.pk_seccion, p.clave_partido
),
satisfaccion AS (
    SELECT 
        pk_seccion,
        indice_satisfaccion_ciudadana,
        total_opiniones
    FROM vw_indice_satisfaccion_seccion
)
SELECT 
    s.seccion,
    g.clave_partido as ganador_2024,
    g.votos as votos_ganador,
    pi.lista_nominal_oficial,
    ROUND(g.votos::numeric * 100 / NULLIF(pi.lista_nominal_oficial, 0), 2) as pct_votos,
    
    COALESCE(sat.indice_satisfaccion_ciudadana, 50) as indice_satisfaccion,
    COALESCE(sat.total_opiniones, 0) as num_opiniones,
    
    CASE 
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 40 THEN 'ALTO RIESGO'
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 60 THEN 'RIESGO MEDIO'
        ELSE 'BAJO RIESGO'
    END as nivel_riesgo_electoral,
    
    CASE 
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 40 THEN 'Operacion politica de cicatrizacion URGENTE'
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 60 THEN 'Reforzar operacion territorial'
        ELSE 'Mantener presencia institucional'
    END as accion_recomendada
    
FROM seccion s
JOIN ganadores_2024 g ON g.pk_seccion = s.pk_seccion AND g.rn = 1
LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = 2024
LEFT JOIN satisfaccion sat ON sat.pk_seccion = s.pk_seccion
WHERE s.id_municipio = 56
ORDER BY indice_satisfaccion ASC;

-- ============================================
-- VISTA: vw_confianza_institucional
-- ============================================
DROP VIEW IF EXISTS vw_confianza_institucional CASCADE;
CREATE VIEW vw_confianza_institucional AS
WITH denuncias_resueltas AS (
    SELECT 
        pk_seccion,
        COUNT(*) as total_denuncias,
        SUM(CASE WHEN estatus = 'RESUELTO' THEN 1 ELSE 0 END) as denuncias_resueltas,
        AVG(tiempo_resolucion_dias) as tiempo_promedio_resolucion
    FROM denuncias_ciudadanas
    WHERE fecha_denuncia >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY pk_seccion
)
SELECT 
    s.seccion,
    s.pk_seccion,
    
    COALESCE(dr.total_denuncias, 0) as total_denuncias_12m,
    COALESCE(dr.denuncias_resueltas, 0) as denuncias_resueltas_12m,
    ROUND(
        COALESCE(dr.denuncias_resueltas, 0)::numeric * 100 / 
        NULLIF(dr.total_denuncias, 0), 
        1
    ) as tasa_resolucion_pct,
    
    ROUND(COALESCE(dr.tiempo_promedio_resolucion, 0), 1) as dias_promedio_resolucion,
    
    ROUND(
        (COALESCE(dr.denuncias_resueltas, 0)::numeric * 100 / NULLIF(dr.total_denuncias, 1)) * 0.7 +
        (CASE 
            WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 7 THEN 100
            WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 15 THEN 75
            WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 30 THEN 50
            ELSE 25
        END) * 0.3,
        1
    ) as indice_confianza_institucional,
    
    CASE 
        WHEN ROUND(
            (COALESCE(dr.denuncias_resueltas, 0)::numeric * 100 / NULLIF(dr.total_denuncias, 1)) * 0.7 +
            (CASE 
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 7 THEN 100
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 15 THEN 75
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 30 THEN 50
                ELSE 25
            END) * 0.3,
            1
        ) >= 80 THEN 'Alta confianza'
        WHEN ROUND(
            (COALESCE(dr.denuncias_resueltas, 0)::numeric * 100 / NULLIF(dr.total_denuncias, 1)) * 0.7 +
            (CASE 
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 7 THEN 100
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 15 THEN 75
                WHEN COALESCE(dr.tiempo_promedio_resolucion, 0) <= 30 THEN 50
                ELSE 25
            END) * 0.3,
            1
        ) >= 60 THEN 'Confianza media'
        ELSE 'Baja confianza'
    END as nivel_confianza
    
FROM seccion s
LEFT JOIN denuncias_resueltas dr ON dr.pk_seccion = s.pk_seccion
WHERE s.id_municipio = 56
ORDER BY indice_confianza_institucional ASC;

-- ============================================
-- VISTA: vw_satisfaccion_por_servicio
-- ============================================
DROP VIEW IF EXISTS vw_satisfaccion_por_servicio CASCADE;
CREATE VIEW vw_satisfaccion_por_servicio AS
SELECT 
    s.seccion,
    cs.nombre_categoria,
    cs.pilar_gobierno,
    
    ROUND(AVG(ss.calificacion), 2) as calificacion_promedio,
    ROUND(AVG(ss.sentimiento_polaridad), 2) as sentimiento_promedio,
    COUNT(*) as total_opiniones,
    
    CASE 
        WHEN AVG(ss.calificacion) >= 4.0 THEN 'Excelente'
        WHEN AVG(ss.calificacion) >= 3.0 THEN 'Bueno'
        WHEN AVG(ss.calificacion) >= 2.0 THEN 'Regular'
        ELSE 'Deficiente'
    END as nivel_desempeno
    
FROM seccion s
JOIN sentimiento_social ss ON ss.pk_seccion = s.pk_seccion
JOIN categoria_servicio cs ON cs.id_categoria = ss.id_categoria
WHERE s.id_municipio = 56
GROUP BY s.seccion, cs.id_categoria, cs.nombre_categoria, cs.pilar_gobierno
ORDER BY s.seccion, calificacion_promedio DESC;

-- ============================================
-- DATOS DE EJEMPLO
-- ============================================
DO $$
DECLARE
    v_seccion_pk INTEGER;
BEGIN
    FOR v_seccion_pk IN 
        SELECT pk_seccion FROM seccion WHERE id_municipio = 56 LIMIT 20
    LOOP
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk, 1, 1,
            FLOOR(RANDOM() * 3 + 2)::INTEGER,
            (RANDOM() * 1.5 - 0.5)::NUMERIC(3,2),
            TRUE
        );
        
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk, 1, 4,
            FLOOR(RANDOM() * 2 + 2)::INTEGER,
            (RANDOM() * 0.6 - 0.6)::NUMERIC(3,2),
            TRUE
        );
        
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk, 2, 3,
            FLOOR(RANDOM() * 2 + 3)::INTEGER,
            (RANDOM() * 0.8)::NUMERIC(3,2),
            TRUE
        );
    END LOOP;
END $$;

-- Verificacion
SELECT 'Esquema creado exitosamente' as status;
