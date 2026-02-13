-- ============================================
-- ESQUEMA: SENTIMIENTO SOCIAL Y SATISFACCIÓN CIUDADANA
-- Autor: Sistema Electoral Taxco
-- Fecha: 2026-02-11
-- ============================================

-- ============================================
-- TABLA: fuente_sentimiento (Catálogo)
-- ============================================
CREATE TABLE IF NOT EXISTS fuente_sentimiento (
    id_fuente SERIAL PRIMARY KEY,
    nombre_fuente VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    peso_confiabilidad NUMERIC(3,2) DEFAULT 1.00,
    CONSTRAINT chk_peso CHECK (peso_confiabilidad BETWEEN 0 AND 1)
);

COMMENT ON TABLE fuente_sentimiento IS 'Catálogo de fuentes de captura de sentimiento';
COMMENT ON COLUMN fuente_sentimiento.peso_confiabilidad IS 'Peso de confiabilidad 0-1 para ponderación';

-- Datos iniciales
INSERT INTO fuente_sentimiento (nombre_fuente, descripcion, peso_confiabilidad) VALUES
('Encuesta Casa por Casa', 'Levantamiento directo con ciudadanos', 1.00),
('Foro Ciudadano', 'Participación en foros municipales', 0.85),
('Redes Sociales', 'Facebook, Twitter/X, WhatsApp', 0.60),
('Denuncias 911', 'Llamadas de emergencia', 0.95),
('Solicitudes Plataforma Municipal', 'Sistema oficial de atención ciudadana', 0.90),
('Buzón Ciudadano', 'Quejas y sugerencias físicas', 0.80)
ON CONFLICT (nombre_fuente) DO NOTHING;

-- ============================================
-- TABLA: categoria_servicio (Catálogo)
-- ============================================
CREATE TABLE IF NOT EXISTS categoria_servicio (
    id_categoria SERIAL PRIMARY KEY,
    nombre_categoria VARCHAR(100) NOT NULL UNIQUE,
    pilar_gobierno VARCHAR(50),
    prioridad_estrategica SMALLINT DEFAULT 3,
    CONSTRAINT chk_prioridad CHECK (prioridad_estrategica BETWEEN 1 AND 5)
);

COMMENT ON TABLE categoria_servicio IS 'Catálogo de categorías de servicios públicos';
COMMENT ON COLUMN categoria_servicio.prioridad_estrategica IS '1=Máxima prioridad, 5=Baja prioridad';

-- Datos iniciales
INSERT INTO categoria_servicio (nombre_categoria, pilar_gobierno, prioridad_estrategica) VALUES
('Agua Potable', 'Servicios Públicos', 1),
('Drenaje y Alcantarillado', 'Servicios Públicos', 1),
('Recolección de Basura', 'Servicios Públicos', 2),
('Seguridad Pública', 'Seguridad y Justicia', 1),
('Alumbrado Público', 'Servicios Públicos', 3),
('Bacheo y Pavimentación', 'Infraestructura', 2),
('Salud y Hospitales', 'Bienestar Social', 1),
('Educación', 'Bienestar Social', 1),
('Empleo y Economía', 'Desarrollo Económico', 2),
('Transporte Público', 'Movilidad', 3),
('Parques y Espacios Públicos', 'Desarrollo Urbano', 4),
('Trámites y Gestión Municipal', 'Gobierno', 3)
ON CONFLICT (nombre_categoria) DO NOTHING;

-- ============================================
-- TABLA PRINCIPAL: sentimiento_social
-- ============================================
CREATE TABLE IF NOT EXISTS sentimiento_social (
    pk_sentimiento SERIAL PRIMARY KEY,
    pk_seccion INTEGER NOT NULL REFERENCES seccion(pk_seccion) ON DELETE CASCADE,
    id_fuente INTEGER NOT NULL REFERENCES fuente_sentimiento(id_fuente),
    id_categoria INTEGER NOT NULL REFERENCES categoria_servicio(id_categoria),
    
    -- Datos del sentimiento
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calificacion SMALLINT NOT NULL,
    sentimiento_polaridad NUMERIC(3,2) NOT NULL,
    comentario TEXT,
    
    -- Metadatos
    respondente_genero CHAR(1),
    respondente_edad_rango VARCHAR(20),
    capturado_por VARCHAR(100),
    validado BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT chk_calificacion CHECK (calificacion BETWEEN 1 AND 5),
    CONSTRAINT chk_polaridad CHECK (sentimiento_polaridad BETWEEN -1 AND 1),
    CONSTRAINT chk_genero CHECK (respondente_genero IN ('M', 'F', 'O', NULL))
);

COMMENT ON TABLE sentimiento_social IS 'Registro de sentimiento y satisfacción ciudadana por sección';
COMMENT ON COLUMN sentimiento_social.calificacion IS 'Escala 1-5: 1=Muy malo, 5=Excelente';
COMMENT ON COLUMN sentimiento_social.sentimiento_polaridad IS 'Polaridad: -1=Muy negativo, 0=Neutral, 1=Muy positivo';

-- Índices para optimización
CREATE INDEX idx_sentimiento_seccion ON sentimiento_social(pk_seccion);
CREATE INDEX idx_sentimiento_fecha ON sentimiento_social(fecha_registro DESC);
CREATE INDEX idx_sentimiento_categoria ON sentimiento_social(id_categoria);
CREATE INDEX idx_sentimiento_fuente ON sentimiento_social(id_fuente);

-- ============================================
-- TABLA: denuncias_ciudadanas
-- ============================================
CREATE TABLE IF NOT EXISTS denuncias_ciudadanas (
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

COMMENT ON TABLE denuncias_ciudadanas IS 'Registro de denuncias y solicitudes ciudadanas';

CREATE INDEX idx_denuncias_seccion ON denuncias_ciudadanas(pk_seccion);
CREATE INDEX idx_denuncias_estatus ON denuncias_ciudadanas(estatus);

-- ============================================
-- VISTA: vw_indice_satisfaccion_seccion
-- ============================================
CREATE OR REPLACE VIEW vw_indice_satisfaccion_seccion AS
SELECT 
    s.seccion,
    s.pk_seccion,
    
    -- Promedio ponderado de calificación
    ROUND(
        SUM(ss.calificacion * fs.peso_confiabilidad) / 
        NULLIF(SUM(fs.peso_confiabilidad), 0), 
        2
    ) as calificacion_promedio,
    
    -- Promedio de sentimiento polaridad
    ROUND(AVG(ss.sentimiento_polaridad), 2) as sentimiento_promedio,
    
    -- Índice de Satisfacción Ciudadana (escala 0-100)
    ROUND(
        (SUM(ss.calificacion * fs.peso_confiabilidad) / 
         NULLIF(SUM(fs.peso_confiabilidad), 0) - 1) * 25, 
        1
    ) as indice_satisfaccion_ciudadana,
    
    -- Total de registros
    COUNT(*) as total_opiniones,
    
    -- Última actualización
    MAX(ss.fecha_registro) as ultima_actualizacion
    
FROM seccion s
LEFT JOIN sentimiento_social ss ON ss.pk_seccion = s.pk_seccion
LEFT JOIN fuente_sentimiento fs ON fs.id_fuente = ss.id_fuente
WHERE s.id_municipio = 56
GROUP BY s.seccion, s.pk_seccion;

COMMENT ON VIEW vw_indice_satisfaccion_seccion IS 'Índice de Satisfacción Ciudadana (ISC) por sección, escala 0-100';

-- ============================================
-- VISTA: vw_riesgo_electoral
-- ============================================
CREATE OR REPLACE VIEW vw_riesgo_electoral AS
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
    
    -- Clasificación de riesgo
    CASE 
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 40 THEN 'ALTO RIESGO'
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 60 THEN 'RIESGO MEDIO'
        ELSE 'BAJO RIESGO'
    END as nivel_riesgo_electoral,
    
    -- Acción recomendada
    CASE 
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 40 THEN 'Operación política de cicatrización URGENTE'
        WHEN COALESCE(sat.indice_satisfaccion_ciudadana, 50) < 60 THEN 'Reforzar operación territorial'
        ELSE 'Mantener presencia institucional'
    END as accion_recomendada
    
FROM seccion s
JOIN ganadores_2024 g ON g.pk_seccion = s.pk_seccion AND g.rn = 1
LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = 2024
LEFT JOIN satisfaccion sat ON sat.pk_seccion = s.pk_seccion
WHERE s.id_municipio = 56
ORDER BY indice_satisfaccion ASC;

COMMENT ON VIEW vw_riesgo_electoral IS 'Identifica secciones con riesgo electoral por bajo índice de satisfacción';

-- ============================================
-- VISTA: vw_confianza_institucional
-- ============================================
CREATE OR REPLACE VIEW vw_confianza_institucional AS
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
    
    -- Tasa de resolución
    COALESCE(dr.total_denuncias, 0) as total_denuncias_12m,
    COALESCE(dr.denuncias_resueltas, 0) as denuncias_resueltas_12m,
    ROUND(
        COALESCE(dr.denuncias_resueltas, 0)::numeric * 100 / 
        NULLIF(dr.total_denuncias, 0), 
        1
    ) as tasa_resolucion_pct,
    
    -- Tiempo promedio
    ROUND(COALESCE(dr.tiempo_promedio_resolucion, 0), 1) as dias_promedio_resolucion,
    
    -- Índice de Confianza Institucional (0-100)
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
    
    -- Clasificación
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

COMMENT ON VIEW vw_confianza_institucional IS 'Índice de Confianza Institucional basado en resolución de denuncias';

-- ============================================
-- VISTA: vw_satisfaccion_por_servicio
-- ============================================
CREATE OR REPLACE VIEW vw_satisfaccion_por_servicio AS
SELECT 
    s.seccion,
    cs.nombre_categoria,
    cs.pilar_gobierno,
    
    ROUND(AVG(ss.calificacion), 2) as calificacion_promedio,
    ROUND(AVG(ss.sentimiento_polaridad), 2) as sentimiento_promedio,
    COUNT(*) as total_opiniones,
    
    -- Clasificación de desempeño
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

COMMENT ON VIEW vw_satisfaccion_por_servicio IS 'Satisfacción ciudadana desglosada por tipo de servicio';

-- ============================================
-- FUNCIÓN: insertar_sentimiento_batch
-- ============================================
CREATE OR REPLACE FUNCTION insertar_sentimiento_batch(
    p_secciones INTEGER[],
    p_fuente VARCHAR,
    p_categoria VARCHAR,
    p_calificacion INTEGER,
    p_polaridad NUMERIC
) RETURNS INTEGER AS $$
DECLARE
    v_id_fuente INTEGER;
    v_id_categoria INTEGER;
    v_count INTEGER := 0;
    v_seccion INTEGER;
BEGIN
    -- Obtener IDs de catálogos
    SELECT id_fuente INTO v_id_fuente 
    FROM fuente_sentimiento 
    WHERE nombre_fuente = p_fuente;
    
    SELECT id_categoria INTO v_id_categoria 
    FROM categoria_servicio 
    WHERE nombre_categoria = p_categoria;
    
    IF v_id_fuente IS NULL OR v_id_categoria IS NULL THEN
        RAISE EXCEPTION 'Fuente o categoría no encontrada';
    END IF;
    
    -- Insertar para cada sección
    FOREACH v_seccion IN ARRAY p_secciones
    LOOP
        INSERT INTO sentimiento_social (
            pk_seccion, id_fuente, id_categoria, 
            calificacion, sentimiento_polaridad, validado
        )
        SELECT 
            pk_seccion, v_id_fuente, v_id_categoria,
            p_calificacion, p_polaridad, TRUE
        FROM seccion
        WHERE seccion = v_seccion AND id_municipio = 56;
        
        v_count := v_count + 1;
    END LOOP;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION insertar_sentimiento_batch IS 'Inserta sentimiento para múltiples secciones simultáneamente';

-- ============================================
-- DATOS DE EJEMPLO (para pruebas)
-- ============================================
-- Insertar sentimientos de ejemplo
DO $$
DECLARE
    v_seccion_pk INTEGER;
BEGIN
    FOR v_seccion_pk IN 
        SELECT pk_seccion FROM seccion WHERE id_municipio = 56 LIMIT 20
    LOOP
        -- Agua potable (calificaciones variables)
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk,
            1, -- Encuesta
            1, -- Agua Potable
            FLOOR(RANDOM() * 3 + 2)::INTEGER, -- 2-4
            (RANDOM() * 1.5 - 0.5)::NUMERIC(3,2), -- -0.5 a 1.0
            TRUE
        );
        
        -- Seguridad
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk,
            1,
            4, -- Seguridad
            FLOOR(RANDOM() * 2 + 2)::INTEGER, -- 2-3
            (RANDOM() * 0.6 - 0.6)::NUMERIC(3,2), -- -0.6 a 0
            TRUE
        );
        
        -- Recolección de basura
        INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado)
        VALUES (
            v_seccion_pk,
            2, -- Foro
            3, -- Basura
            FLOOR(RANDOM() * 2 + 3)::INTEGER, -- 3-4
            (RANDOM() * 0.8)::NUMERIC(3,2), -- 0 a 0.8
            TRUE
        );
    END LOOP;
END $$;

-- ============================================
-- GRANTS (Permisos)
-- ============================================
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO usuario_consulta;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO usuario_admin;

-- ============================================
-- VALIDACIÓN FINAL
-- ============================================
SELECT 'Esquema de Sentimiento Social creado exitosamente' as mensaje;

SELECT 
    'sentimiento_social' as tabla, 
    COUNT(*) as registros 
FROM sentimiento_social
UNION ALL
SELECT 'fuente_sentimiento', COUNT(*) FROM fuente_sentimiento
UNION ALL
SELECT 'categoria_servicio', COUNT(*) FROM categoria_servicio;

-- Verificar vistas
SELECT 
    viewname as vista,
    definition as definicion_preview
FROM pg_views
WHERE schemaname = 'public' 
  AND viewname LIKE 'vw_%satisfaccion%' OR viewname LIKE 'vw_riesgo%' OR viewname LIKE 'vw_confianza%';
