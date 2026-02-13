-- ============================================
-- ESQUEMA DE BASE DE DATOS TAXCO ELECTORAL
-- Versión: 1.0 - Con control de calidad
-- ============================================

-- Catálogo de municipios
CREATE TABLE municipio (
    id_municipio       SMALLINT    PRIMARY KEY,
    nombre_municipio   VARCHAR(100) NOT NULL,
    poblacion_total    INTEGER     NULL,
    coef_gini_ref      NUMERIC(5,3) NULL
);

INSERT INTO municipio (id_municipio, nombre_municipio, poblacion_total, coef_gini_ref)
VALUES (56, 'Taxco de Alarcón', 99111, 0.417);

COMMENT ON TABLE municipio IS 'Catálogo de municipios con indicadores de referencia';

-- Catálogo de secciones
CREATE TABLE seccion (
    pk_seccion          SERIAL        PRIMARY KEY,
    id_municipio        SMALLINT      NOT NULL REFERENCES municipio(id_municipio),
    seccion             INTEGER       NOT NULL,
    distrito_local      SMALLINT      NULL,
    distrito_federal    SMALLINT      NULL,
    tiene_datos_electorales BOOLEAN   NOT NULL DEFAULT TRUE,
    observaciones       TEXT          NULL,
    UNIQUE (id_municipio, seccion)
);

CREATE INDEX idx_seccion_numero ON seccion(seccion);

COMMENT ON TABLE seccion IS 'Catálogo geográfico de secciones electorales';
COMMENT ON COLUMN seccion.tiene_datos_electorales IS 'FALSE si la sección existe en INEGI pero no tiene casillas instaladas';

-- Catálogo de elecciones
CREATE TABLE eleccion (
    id_eleccion   SERIAL        PRIMARY KEY,
    anio          SMALLINT      NOT NULL,
    ambito        VARCHAR(30)   NOT NULL,
    descripcion   VARCHAR(150)  NOT NULL,
    UNIQUE (anio, ambito)
);

INSERT INTO eleccion (anio, ambito, descripcion) VALUES
(2018, 'LOCAL', 'Diputaciones locales Guerrero 2018'),
(2021, 'LOCAL', 'Diputaciones locales Guerrero 2021'),
(2024, 'LOCAL', 'Diputaciones locales Guerrero 2024');

COMMENT ON TABLE eleccion IS 'Catálogo de procesos electorales';

-- Catálogo de partidos (llenaremos después con ETL)
CREATE TABLE partido (
    id_partido     SERIAL       PRIMARY KEY,
    clave_partido  VARCHAR(20)  NOT NULL UNIQUE,
    nombre_largo   VARCHAR(150) NOT NULL,
    es_coalicion   BOOLEAN      NOT NULL DEFAULT FALSE,
    anio_inicio    SMALLINT     NULL,
    anio_fin       SMALLINT     NULL
);

COMMENT ON TABLE partido IS 'Catálogo de partidos y coaliciones (histórico)';

-- Tabla de casillas
CREATE TABLE casilla (
    pk_casilla        SERIAL      PRIMARY KEY,
    pk_seccion        INTEGER     NOT NULL REFERENCES seccion(pk_seccion),
    id_eleccion       INTEGER     NOT NULL REFERENCES eleccion(id_eleccion),
    clave_casilla     VARCHAR(10) NOT NULL,
    tipo_casilla      VARCHAR(20) NULL,
    UNIQUE (pk_seccion, id_eleccion, clave_casilla)
);

CREATE INDEX idx_casilla_seccion ON casilla(pk_seccion);
CREATE INDEX idx_casilla_eleccion ON casilla(id_eleccion);

COMMENT ON TABLE casilla IS 'Casillas instaladas por sección y elección';
COMMENT ON COLUMN casilla.tipo_casilla IS 'BASICA, CONTIGUA, ESPECIAL, EXTRAORDINARIA';

-- Resultados electorales (totales por casilla)
CREATE TABLE resultados_electorales (
    pk_resultado         SERIAL      PRIMARY KEY,
    pk_casilla           INTEGER     NOT NULL REFERENCES casilla(pk_casilla) ON DELETE CASCADE,
    num_votos_validos    INTEGER     NOT NULL,
    num_votos_cannreg    INTEGER     NOT NULL,
    num_votos_nulos      INTEGER     NOT NULL,
    total_votos          INTEGER     NOT NULL,
    lista_nominal_acta   INTEGER     NOT NULL,
    
    -- Control de calidad
    flag_calidad         VARCHAR(30) NOT NULL DEFAULT 'VALIDO',
    observaciones_calidad TEXT       NULL,
    
    fuente               VARCHAR(50) NOT NULL,
    fecha_carga          TIMESTAMP   NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_calidad CHECK (flag_calidad IN (
        'VALIDO', 
        'TOTAL_INCORRECTO', 
        'EXCEDE_LISTA',
        'CASILLA_ESPECIAL',
        'CASILLA_ESPECIAL_CORREGIDA'
    )),
    CONSTRAINT chk_votos_positivos CHECK (
        num_votos_validos >= 0 AND 
        num_votos_cannreg >= 0 AND 
        num_votos_nulos >= 0 AND
        total_votos >= 0 AND
        lista_nominal_acta >= 0
    )
);

CREATE INDEX idx_resultado_casilla ON resultados_electorales(pk_casilla);
CREATE INDEX idx_resultado_calidad ON resultados_electorales(flag_calidad);

COMMENT ON TABLE resultados_electorales IS 'Totales de votación por casilla con control de calidad';
COMMENT ON COLUMN resultados_electorales.flag_calidad IS 'VALIDO: sin problemas | EXCEDE_LISTA: total > lista nominal | CASILLA_ESPECIAL: casilla B/C/E corregida';

-- Detalle de votos por partido
CREATE TABLE resultados_partido (
    pk_resultado_partido  SERIAL   PRIMARY KEY,
    pk_resultado          INTEGER  NOT NULL REFERENCES resultados_electorales(pk_resultado) ON DELETE CASCADE,
    id_partido            INTEGER  NOT NULL REFERENCES partido(id_partido),
    votos                 INTEGER  NOT NULL,
    UNIQUE (pk_resultado, id_partido),
    CONSTRAINT chk_votos_partido_positivos CHECK (votos >= 0)
);

CREATE INDEX idx_resultado_partido_resultado ON resultados_partido(pk_resultado);
CREATE INDEX idx_resultado_partido_partido ON resultados_partido(id_partido);

COMMENT ON TABLE resultados_partido IS 'Detalle de votación por partido/coalición';

-- Padrón INE (lista nominal oficial)
CREATE TABLE padron_ine (
    pk_seccion           INTEGER     NOT NULL REFERENCES seccion(pk_seccion),
    lista_hombres        INTEGER     NOT NULL,
    lista_mujeres        INTEGER     NOT NULL,
    lista_nominal_oficial INTEGER    NOT NULL,
    anio_padron          SMALLINT    NOT NULL,
    fuente               VARCHAR(50) NOT NULL,
    fecha_carga          TIMESTAMP   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (pk_seccion, anio_padron),
    CONSTRAINT chk_lista_nominal_consistente CHECK (
        lista_nominal_oficial = lista_hombres + lista_mujeres
    )
);

CREATE INDEX idx_padron_anio ON padron_ine(anio_padron);

COMMENT ON TABLE padron_ine IS 'Lista nominal oficial del INE por sección';

-- Indicadores INEGI por sección
CREATE TABLE carencias_inegi (
    pk_seccion         INTEGER     NOT NULL REFERENCES seccion(pk_seccion),
    anio_inegi         SMALLINT    NOT NULL,
    
    -- Demografía básica
    pobtot             INTEGER     NOT NULL,
    grado_prom_escolar NUMERIC(5,2) NOT NULL,
    
    -- Salud (Pilar 1)
    pob_sin_derechohab    INTEGER   NOT NULL,
    pob_con_derechohab    INTEGER   NOT NULL,
    pct_sin_derechohab    NUMERIC(5,2) NULL,
    
    -- Mercado laboral
    pea                  INTEGER     NOT NULL,
    pe_inactiva          INTEGER     NOT NULL,
    pob_ocupada          INTEGER     NOT NULL,
    pob_desocupada       INTEGER     NOT NULL,
    
    -- Vivienda (Pilar 3)
    num_viviendas_particulares  INTEGER NOT NULL,
    promedio_ocupantes          NUMERIC(4,2) NOT NULL,
    
    -- Servicios básicos y TIC (Pilar 4)
    vph_autom              INTEGER  NOT NULL,
    vph_pc                 INTEGER  NOT NULL,
    vph_cel                INTEGER  NOT NULL,
    vph_internet           INTEGER  NOT NULL,
    
    -- Campos futuros para completar pilares
    vph_sin_agua           INTEGER  NULL,
    vph_sin_drenaje        INTEGER  NULL,
    vph_sin_electricidad   INTEGER  NULL,
    vph_piso_tierra        INTEGER  NULL,
    
    fuente                VARCHAR(50) NOT NULL,
    fecha_carga           TIMESTAMP   NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (pk_seccion, anio_inegi)
);

CREATE INDEX idx_carencias_anio ON carencias_inegi(anio_inegi);

COMMENT ON TABLE carencias_inegi IS 'Indicadores socioeconómicos INEGI por sección (Censo 2020)';
COMMENT ON COLUMN carencias_inegi.pct_sin_derechohab IS 'Porcentaje de población sin derechohabiencia a servicios de salud';

-- Tabla de log de inconsistencias
CREATE TABLE log_inconsistencias (
    pk_log            SERIAL      PRIMARY KEY,
    anio_eleccion     SMALLINT    NOT NULL,
    seccion           INTEGER     NOT NULL,
    casilla           VARCHAR(10) NOT NULL,
    tipo_inconsistencia VARCHAR(50) NOT NULL,
    descripcion       TEXT        NOT NULL,
    valor_original    TEXT        NULL,
    valor_corregido   TEXT        NULL,
    fecha_deteccion   TIMESTAMP   NOT NULL DEFAULT NOW(),
    fuente            VARCHAR(50) NOT NULL
);

CREATE INDEX idx_log_anio_seccion ON log_inconsistencias(anio_eleccion, seccion);

COMMENT ON TABLE log_inconsistencias IS 'Registro de auditoría de todas las inconsistencias detectadas en datos fuente';

-- ============================================
-- VISTAS ANALÍTICAS
-- ============================================

-- Vista 1: Participación real por sección y año
CREATE OR REPLACE VIEW vw_participacion_seccion_anio AS
SELECT
    s.pk_seccion,
    s.seccion,
    e.anio,
    e.ambito,
    SUM(re.total_votos) AS total_votos_seccion,
    pi.lista_nominal_oficial,
    CASE
        WHEN pi.lista_nominal_oficial > 0 THEN
            ROUND(SUM(re.total_votos)::numeric * 100.0 / pi.lista_nominal_oficial, 2)
        ELSE NULL
    END AS participacion_real_pct,
    COUNT(c.pk_casilla) AS num_casillas_instaladas
FROM seccion s
JOIN casilla c ON c.pk_seccion = s.pk_seccion
JOIN eleccion e ON e.id_eleccion = c.id_eleccion
JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = e.anio
GROUP BY s.pk_seccion, s.seccion, e.anio, e.ambito, pi.lista_nominal_oficial;

COMMENT ON VIEW vw_participacion_seccion_anio IS 'Participación electoral real por sección y año';

-- Vista 2: Índice de brecha de servicios
CREATE OR REPLACE VIEW vw_brecha_servicios AS
WITH base AS (
    SELECT
        vpsa.pk_seccion,
        vpsa.seccion,
        vpsa.anio,
        vpsa.participacion_real_pct,
        ci.anio_inegi,
        ci.pobtot,
        ci.pct_sin_derechohab,
        ci.grado_prom_escolar,
        ci.vph_internet,
        ci.vph_cel,
        ci.vph_pc,
        ci.vph_autom,
        ci.promedio_ocupantes,
        -- Indicadores de carencia (cuando estén disponibles)
        ci.vph_sin_agua,
        ci.vph_sin_drenaje,
        ci.vph_sin_electricidad,
        ci.vph_piso_tierra
    FROM vw_participacion_seccion_anio vpsa
    JOIN carencias_inegi ci ON ci.pk_seccion = vpsa.pk_seccion
)
SELECT
    *,
    -- Índice de penetración TIC (0-100)
    CASE WHEN pobtot > 0 
         THEN ROUND((vph_internet::numeric + vph_pc + vph_cel) * 100.0 / (pobtot * 3), 2)
         ELSE NULL END AS indice_tic,
    -- Clasificación de participación
    CASE 
        WHEN participacion_real_pct >= 70 THEN 'ALTA'
        WHEN participacion_real_pct >= 50 THEN 'MEDIA'
        WHEN participacion_real_pct >= 30 THEN 'BAJA'
        ELSE 'MUY_BAJA'
    END AS clasificacion_participacion
FROM base;

COMMENT ON VIEW vw_brecha_servicios IS 'Cruce de participación electoral con indicadores de servicios y desarrollo';

-- Vista 3: Calidad de datos por año
CREATE OR REPLACE VIEW vw_calidad_datos AS
SELECT
    e.anio,
    e.ambito,
    re.flag_calidad,
    COUNT(*) AS num_casillas,
    SUM(re.total_votos) AS total_votos,
    ROUND(AVG(re.total_votos), 2) AS promedio_votos_casilla,
    COUNT(DISTINCT c.pk_seccion) AS num_secciones
FROM eleccion e
JOIN casilla c ON c.id_eleccion = e.id_eleccion
JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
GROUP BY e.anio, e.ambito, re.flag_calidad
ORDER BY e.anio, re.flag_calidad;

COMMENT ON VIEW vw_calidad_datos IS 'Estadísticas de calidad de datos por año electoral';

-- Vista 4: Comparación de lista nominal (actas vs padrón)
CREATE OR REPLACE VIEW vw_comparacion_lista_nominal AS
SELECT
    s.seccion,
    e.anio,
    SUM(re.lista_nominal_acta) AS ln_suma_actas,
    pi.lista_nominal_oficial AS ln_padron_oficial,
    SUM(re.lista_nominal_acta) - pi.lista_nominal_oficial AS diferencia,
    CASE 
        WHEN pi.lista_nominal_oficial > 0 THEN
            ROUND((SUM(re.lista_nominal_acta) - pi.lista_nominal_oficial)::numeric * 100.0 / pi.lista_nominal_oficial, 2)
        ELSE NULL
    END AS pct_diferencia
FROM seccion s
JOIN casilla c ON c.pk_seccion = s.pk_seccion
JOIN eleccion e ON e.id_eleccion = c.id_eleccion
JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = e.anio
GROUP BY s.seccion, e.anio, pi.lista_nominal_oficial
HAVING SUM(re.lista_nominal_acta) - pi.lista_nominal_oficial <> 0;

COMMENT ON VIEW vw_comparacion_lista_nominal IS 'Discrepancias entre lista nominal de actas y padrón oficial INE';

-- ============================================
-- PERMISOS Y SEGURIDAD
-- ============================================

-- Grants básicos (ajusta según tu estructura de usuarios)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO taxco_readonly;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO taxco_admin;
