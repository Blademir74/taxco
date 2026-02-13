-- Habilitar extensión PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Agregar columna de geometría a seccion
ALTER TABLE seccion 
ADD COLUMN geom GEOMETRY(MULTIPOLYGON, 4326);

-- Crear índice espacial
CREATE INDEX idx_seccion_geom ON seccion USING GIST(geom);

-- Comentario
COMMENT ON COLUMN seccion.geom IS 'Geometría (polígono) de la sección electoral en WGS84 (EPSG:4326)';

-- Verificar
SELECT PostGIS_Version();
