-- ============================================
-- fix_encoding_postgresql.sql
-- 
-- Script SQL para configurar permanentemente UTF-8 
-- en la base de datos taxco_electoral
--
-- EJECUTAR EN psql COMO USUARIO postgres:
-- psql -U postgres -d taxco_electoral -f fix_encoding_postgresql.sql
-- ============================================

-- Verificar configuración actual
\echo '=== CONFIGURACIÓN ACTUAL DE ENCODING ==='
SHOW server_encoding;
SHOW client_encoding;

SELECT 
    datname,
    pg_encoding_to_char(encoding) as encoding,
    datcollate,
    datctype
FROM pg_database 
WHERE datname = 'taxco_electoral';

\echo ''
\echo '=== APLICANDO CONFIGURACIONES UTF-8 ==='

-- 1. Forzar client_encoding a UTF8 para la base de datos
ALTER DATABASE taxco_electoral SET client_encoding TO 'UTF8';

-- 2. Configurar TimeZone (opcional pero recomendado)
ALTER DATABASE taxco_electoral SET timezone TO 'America/Mexico_City';

-- 3. Configurar locale para búsquedas case-insensitive en español
-- (opcional, solo si necesitas búsquedas con acentos)
-- ALTER DATABASE taxco_electoral SET lc_collate TO 'es_MX.UTF-8';
-- ALTER DATABASE taxco_electoral SET lc_ctype TO 'es_MX.UTF-8';

-- 4. Optimizaciones de rendimiento (opcional)
ALTER DATABASE taxco_electoral SET max_parallel_workers_per_gather = 4;
ALTER DATABASE taxco_electoral SET effective_cache_size = '4GB';

\echo ''
\echo '=== VERIFICAR CAMBIOS ==='

-- Verificar que los cambios se aplicaron
SELECT 
    datname,
    pg_encoding_to_char(encoding) as encoding,
    datcollate,
    datctype
FROM pg_database 
WHERE datname = 'taxco_electoral';

-- Ver todas las configuraciones de la base de datos
SELECT name, setting 
FROM pg_db_role_setting drs
JOIN pg_database db ON db.oid = drs.setdatabase
JOIN pg_settings ps ON ps.name = drs.setconfig[1]
WHERE db.datname = 'taxco_electoral'
ORDER BY name;

\echo ''
\echo '=== TEST DE CARACTERES ESPECIALES ==='

-- Test rápido de caracteres con acentos
SELECT 
    'Taxco de Alarcón' as municipio,
    'José María Morelos' as personaje,
    'Año 2024 - Elección' as periodo;

\echo ''
\echo '✅ CONFIGURACIÓN COMPLETADA'
\echo ''
\echo 'IMPORTANTE: Para que los cambios tomen efecto:'
\echo '1. Cierra todas las conexiones activas a taxco_electoral'
\echo '2. Reconecta tu aplicación Python'
\echo '3. Ejecuta: python test_conexion.py'
\echo ''

-- ============================================
-- COMANDOS ADICIONALES (ejecutar solo si es necesario)
-- ============================================

-- Si necesitas recrear la base de datos con UTF-8 (CUIDADO: borra datos)
-- NO EJECUTAR a menos que sea absolutamente necesario

/*
DROP DATABASE IF EXISTS taxco_electoral;
CREATE DATABASE taxco_electoral
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Mexico.1252'
    LC_CTYPE = 'Spanish_Mexico.1252'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

\c taxco_electoral

-- Aquí deberías restaurar tu backup:
-- \i backup_taxco_electoral.sql
*/

-- ============================================
-- VERIFICACIÓN DE TABLAS CON DATOS PROBLEMÁTICOS
-- ============================================

\echo ''
\echo '=== VERIFICANDO TABLAS CON POSIBLES CARACTERES PROBLEMÁTICOS ==='

-- Buscar municipios con acentos
SELECT 
    COUNT(*) as total_municipios,
    COUNT(CASE WHEN nombre_municipio LIKE '%ó%' THEN 1 END) as con_o_acentuada
FROM municipio
WHERE nombre_municipio IS NOT NULL;

-- Buscar partidos con caracteres especiales
SELECT DISTINCT clave_partido 
FROM partido 
ORDER BY clave_partido;

-- Verificar que las secciones tienen geometrías válidas
SELECT 
    COUNT(*) as total_secciones,
    COUNT(CASE WHEN geom IS NOT NULL THEN 1 END) as con_geometria
FROM seccion
WHERE id_municipio = 56;

\echo ''
\echo '=== DIAGNÓSTICO COMPLETO ==='
\echo 'Si ves caracteres corruptos arriba (como � o Ã³), significa que:'
\echo '1. Los datos se insertaron con encoding incorrecto'
\echo '2. Necesitas re-importar los datos con UTF-8'
\echo ''