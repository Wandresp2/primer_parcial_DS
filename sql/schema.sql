-- ============================================================================
-- ESQUEMA DE BASE DE DATOS — Óptica y Fotónica (NIST Atomic Spectra Database)
-- Primer Parcial — Desarrollo de Software
-- Estudiante: Perez Criollo Andres David
-- ============================================================================
--
-- Este script contiene UNICAMENTE DDL (definicion de estructura). No inserta
-- ningun dato: la carga se hace despues, de forma automatizada, desde el
-- notebook notebooks/05_pipeline_etl_mysql.ipynb.
--
-- Orden de ejecucion del proyecto:
--   1. docker compose up -d          (levanta MySQL y crea la base db_prueba)
--   2. Ejecutar este archivo en DBeaver, conectado a db_prueba   <-- este script
--   3. Ejecutar notebooks/05_pipeline_etl_mysql.ipynb            (puebla las tablas)
--
-- El script es RECONSTRUIBLE DESDE CERO: puede ejecutarse cuantas veces se
-- quiera, porque empieza eliminando (si existen) la vista y las 9 tablas en
-- el orden inverso de sus dependencias, y luego las vuelve a crear.
--
-- Diseno relacional completo, justificado y verificado contra los datos
-- reales en: docs/PROPUESTA_modelo_relacional.md
-- Origen de los datos y proceso de limpieza en: docs/PLAN_limpieza_datos.md
--                                            y docs/RESULTADOS_exploracion_y_limpieza.md
-- ============================================================================

USE db_prueba;

-- ----------------------------------------------------------------------------
-- 0. Limpieza previa (permite reconstruir el esquema desde cero)
-- ----------------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS v_linea_analisis;

DROP TABLE IF EXISTS linea_referencia;
DROP TABLE IF EXISTS nivel_referencia;
DROP TABLE IF EXISTS linea_espectral;
DROP TABLE IF EXISTS nivel_energia;
DROP TABLE IF EXISTS espectro;
DROP TABLE IF EXISTS referencia;
DROP TABLE IF EXISTS exactitud;
DROP TABLE IF EXISTS tipo_transicion;
DROP TABLE IF EXISTS elemento;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 1. CATALOGOS (sin dependencias)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- elemento — los 10 primeros elementos de la tabla periodica (H a Ne)
-- ----------------------------------------------------------------------------
CREATE TABLE elemento (
    id_elemento     TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simbolo         VARCHAR(3)       NOT NULL,
    nombre          VARCHAR(20)      NOT NULL,
    numero_atomico  TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (id_elemento),
    UNIQUE KEY uq_elemento_simbolo (simbolo),
    UNIQUE KEY uq_elemento_numero_atomico (numero_atomico)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Elementos quimicos del catalogo NIST ASD (H a Ne)';

-- ----------------------------------------------------------------------------
-- tipo_transicion — clasificacion de la transicion electronica (E1/E2/M1/M2/UT)
-- ----------------------------------------------------------------------------
CREATE TABLE tipo_transicion (
    codigo          VARCHAR(4)   NOT NULL,
    nombre          VARCHAR(40)  NOT NULL,
    es_permitida    BOOLEAN      NOT NULL,
    descripcion     VARCHAR(255) NULL,
    PRIMARY KEY (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='E1=dipolo electrico (permitida); E2/M1/M2=prohibidas; UT=sin clasificar';

-- ----------------------------------------------------------------------------
-- exactitud — escala ordinal de calidad del dato Aki, segun el NIST
-- ----------------------------------------------------------------------------
CREATE TABLE exactitud (
    codigo              VARCHAR(3)   NOT NULL,
    orden               TINYINT UNSIGNED NOT NULL,
    tolerancia_max_pct  DECIMAL(6,2) NULL,
    descripcion         VARCHAR(100) NULL,
    PRIMARY KEY (codigo),
    UNIQUE KEY uq_exactitud_orden (orden)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Escala AAA (mejor) a E (peor). El atributo orden permite comparaciones (<, >, BETWEEN)';

-- ----------------------------------------------------------------------------
-- referencia — codigos bibliograficos citados por lineas y niveles
-- ----------------------------------------------------------------------------
CREATE TABLE referencia (
    codigo      VARCHAR(20)                             NOT NULL,
    tipo_fuente ENUM('nivel', 'linea', 'probabilidad')   NULL,
    PRIMARY KEY (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Catalogo de referencias bibliograficas del NIST. Corrige la violacion de 1FN de los campos *_ref, que en el CSV traen listas separadas por comas';

-- ============================================================================
-- 2. ENTIDADES PRINCIPALES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- espectro — un elemento en un estado de ionizacion concreto (ej. 'Ne II')
-- ----------------------------------------------------------------------------
CREATE TABLE espectro (
    id_espectro        TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_elemento        TINYINT UNSIGNED NOT NULL,
    estado_ionizacion  TINYINT UNSIGNED NOT NULL COMMENT '1=neutro, 2=una vez ionizado',
    notacion           VARCHAR(8)       NOT NULL COMMENT 'Ej. "H I", "Ne II"',
    PRIMARY KEY (id_espectro),
    UNIQUE KEY uq_espectro_notacion (notacion),
    UNIQUE KEY uq_espectro_elemento_ion (id_elemento, estado_ionizacion),
    CONSTRAINT fk_espectro_elemento
        FOREIGN KEY (id_elemento) REFERENCES elemento (id_elemento)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Espectros atomicos: elemento + estado de ionizacion';

-- ----------------------------------------------------------------------------
-- nivel_energia — un escalon de energia interno del atomo
-- ----------------------------------------------------------------------------
CREATE TABLE nivel_energia (
    id_nivel                VARCHAR(20)      NOT NULL COMMENT 'Level ID del NIST, ej. 006002.000001. VARCHAR para no perder los ceros a la izquierda',
    id_espectro             TINYINT UNSIGNED NOT NULL,
    configuracion           VARCHAR(80)      NULL COMMENT 'Configuracion electronica, ej. 2s2.2p2.(3P).3d',
    termino                 VARCHAR(20)      NULL COMMENT 'Termino espectroscopico, ej. 2P*',
    j_valor                 DECIMAL(4,1)     NULL COMMENT 'Momento angular total (1.5 para 3/2)',
    j_texto                 VARCHAR(20)      NULL COMMENT 'Valor original de J, incluidos los no resueltos',
    j_resuelto              BOOLEAN          NULL COMMENT 'FALSE si el NIST no determino un unico valor de J',
    g                       SMALLINT UNSIGNED NULL COMMENT 'Degeneracion estadistica del nivel',
    energia_ev              DECIMAL(18,9)    NULL,
    energia_interpolada     BOOLEAN          NOT NULL DEFAULT FALSE COMMENT 'TRUE si la energia es calculada/teorica, no medida',
    incertidumbre_ev        DECIMAL(18,12)   NULL,
    PRIMARY KEY (id_nivel),
    KEY idx_nivel_espectro (id_espectro),
    CONSTRAINT fk_nivel_espectro
        FOREIGN KEY (id_espectro) REFERENCES espectro (id_espectro)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    -- g = 2J+1 se cumple en el 100% de los 5570 niveles donde J esta resuelto.
    -- 130 niveles tienen g documentado pero J sin resolver: por eso g NO se
    -- deriva como columna generada (se perderian esos 130 registros), sino que
    -- se almacena junto con J y esta restriccion impide que se contradigan.
    -- Ver docs/PROPUESTA_modelo_relacional.md, seccion 6.2.
    CONSTRAINT chk_nivel_degeneracion
        CHECK (j_valor IS NULL OR g IS NULL OR g = 2 * j_valor + 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Niveles de energia atomicos (escalones internos del atomo)';

-- ----------------------------------------------------------------------------
-- linea_espectral — un salto de un electron entre DOS niveles, que emite luz
-- ----------------------------------------------------------------------------
CREATE TABLE linea_espectral (
    id_linea                              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_espectro                           TINYINT UNSIGNED NOT NULL,
    id_nivel_inferior                     VARCHAR(20)  NULL COMMENT 'Nulo en 215 lineas sin ID de nivel en el NIST',
    id_nivel_superior                     VARCHAR(20)  NULL,
    codigo_tipo_transicion                VARCHAR(4)   NOT NULL,
    codigo_exactitud                      VARCHAR(3)   NULL COMMENT 'Nulo en las lineas sin Aki documentado',

    longitud_onda_nm                      DECIMAL(18,6) NOT NULL COMMENT 'Valor definitivo: observada, o Ritz si falta',
    longitud_onda_origen                  ENUM('observada', 'ritz') NOT NULL,
    medio                                 ENUM('aire', 'vacio')     NOT NULL,
    longitud_onda_obs_nm                  DECIMAL(18,6) NULL COMMENT 'Medida en laboratorio',
    longitud_onda_ritz_nm                 DECIMAL(18,6) NULL COMMENT 'Calculada de la diferencia de niveles',
    ritz_es_limite                        BOOLEAN       NULL,
    incertidumbre_obs_nm                  DOUBLE NULL COMMENT 'Rango real 1.5e-12 a 9e9: DOUBLE, no DECIMAL (mismo motivo que aki_s1)',
    incertidumbre_ritz_nm                 DOUBLE NULL COMMENT 'Rango real 1.5e-12 a 6e9: DOUBLE, no DECIMAL',

    aki_s1                                DOUBLE  NULL COMMENT 'Coeficiente de Einstein: abarca 35 ordenes de magnitud, por eso DOUBLE y no DECIMAL',
    fuerza_oscilador_fik                  DOUBLE  NULL,
    log_gf                                DECIMAL(10,5) NULL COMMENT 'NO se deriva de g_i*fik: solo coincide en 92.84% de los casos (ver propuesta, seccion 6.3)',

    intensidad_valor                      DOUBLE       NULL COMMENT 'Escala arbitraria propia de cada espectro',
    intensidad_bandera                    VARCHAR(40)  NULL COMMENT 'Bandera de calidad de la linea (*, a, a*, bl(O II,N II)*, ...)',

    energia_inferior_cm1                  DECIMAL(18,6) NULL,
    energia_superior_cm1                  DECIMAL(18,6) NULL,
    energia_inferior_interpolada          BOOLEAN NULL,
    energia_superior_interpolada          BOOLEAN NULL,
    energia_inferior_origen_desconocido   BOOLEAN NULL,
    energia_superior_origen_desconocido   BOOLEAN NULL,

    medicion_repetida                     BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'TRUE si esta misma transicion fue publicada por mas de una fuente',

    PRIMARY KEY (id_linea),
    KEY idx_linea_espectro (id_espectro),
    KEY idx_linea_nivel_inferior (id_nivel_inferior),
    KEY idx_linea_nivel_superior (id_nivel_superior),
    KEY idx_linea_tipo_transicion (codigo_tipo_transicion),
    KEY idx_linea_exactitud (codigo_exactitud),

    CONSTRAINT fk_linea_espectro
        FOREIGN KEY (id_espectro) REFERENCES espectro (id_espectro)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    -- Doble FK a la MISMA tabla: una linea espectral ES un salto entre dos
    -- niveles. Se necesitan dos claves foraneas distintas para representar
    -- el nivel de origen y el nivel de destino del electron.
    CONSTRAINT fk_linea_nivel_inferior
        FOREIGN KEY (id_nivel_inferior) REFERENCES nivel_energia (id_nivel)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_linea_nivel_superior
        FOREIGN KEY (id_nivel_superior) REFERENCES nivel_energia (id_nivel)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_linea_tipo_transicion
        FOREIGN KEY (codigo_tipo_transicion) REFERENCES tipo_transicion (codigo)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_linea_exactitud
        FOREIGN KEY (codigo_exactitud) REFERENCES exactitud (codigo)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    -- Validaciones fisicas: verificadas contra los datos reales (0 violaciones
    -- en 18288 lineas). Se hacen cumplir tambien a nivel de motor de BD.
    CONSTRAINT chk_linea_longitud_onda_positiva
        CHECK (longitud_onda_nm > 0),
    CONSTRAINT chk_linea_aki_positivo
        CHECK (aki_s1 IS NULL OR aki_s1 > 0),
    CONSTRAINT chk_linea_energia_superior_mayor
        CHECK (energia_superior_cm1 IS NULL OR energia_inferior_cm1 IS NULL
               OR energia_superior_cm1 > energia_inferior_cm1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Lineas espectrales: transiciones electronicas entre dos niveles de energia';

-- ============================================================================
-- 3. TABLAS PUENTE (relaciones N:M — corrigen la violacion de 1FN)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- linea_referencia — que referencias documentan cada linea, y para que dato
-- ----------------------------------------------------------------------------
CREATE TABLE linea_referencia (
    id_linea           INT UNSIGNED NOT NULL,
    codigo_referencia  VARCHAR(20)  NOT NULL,
    rol                ENUM('probabilidad', 'longitud_onda') NOT NULL
        COMMENT 'La misma publicacion puede ser fuente de dos hechos distintos de la misma linea',
    PRIMARY KEY (id_linea, codigo_referencia, rol),
    KEY idx_linea_referencia_codigo (codigo_referencia),
    CONSTRAINT fk_linea_referencia_linea
        FOREIGN KEY (id_linea) REFERENCES linea_espectral (id_linea)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_linea_referencia_referencia
        FOREIGN KEY (codigo_referencia) REFERENCES referencia (codigo)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='N:M entre linea_espectral y referencia. Resuelve las listas separadas por comas de tp_ref/line_ref';

-- ----------------------------------------------------------------------------
-- nivel_referencia — que referencias documentan cada nivel de energia
-- ----------------------------------------------------------------------------
CREATE TABLE nivel_referencia (
    id_nivel           VARCHAR(20) NOT NULL,
    codigo_referencia  VARCHAR(20) NOT NULL,
    PRIMARY KEY (id_nivel, codigo_referencia),
    KEY idx_nivel_referencia_codigo (codigo_referencia),
    CONSTRAINT fk_nivel_referencia_nivel
        FOREIGN KEY (id_nivel) REFERENCES nivel_energia (id_nivel)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_nivel_referencia_referencia
        FOREIGN KEY (codigo_referencia) REFERENCES referencia (codigo)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='N:M entre nivel_energia y referencia. Resuelve las listas separadas por comas de Reference';

-- ============================================================================
-- 4. VISTA — atributos derivados (evita dependencias transitivas / viola 3FN)
-- ============================================================================
-- region_espectral, longitud_onda_vacio_nm, log10_aki y energia_foton_ev son
-- funciones de otras columnas no clave de linea_espectral. Almacenarlas violaria
-- la 3FN y arriesgaria inconsistencias. Se calculan al vuelo en esta vista.
-- Ver docs/PROPUESTA_modelo_relacional.md, seccion 6.1.
CREATE OR REPLACE VIEW v_linea_analisis AS
SELECT
    l.id_linea,
    e.notacion                                                     AS espectro,
    el.simbolo                                                     AS elemento,
    el.nombre                                                      AS nombre_elemento,
    l.longitud_onda_nm,
    CASE WHEN l.medio = 'aire'
         THEN l.longitud_onda_nm * 1.00028
         ELSE l.longitud_onda_nm
    END                                                             AS longitud_onda_vacio_nm,
    CASE
        WHEN l.longitud_onda_nm < 10   THEN 'Rayos X'
        WHEN l.longitud_onda_nm < 380  THEN 'Ultravioleta'
        WHEN l.longitud_onda_nm <= 780 THEN 'Visible'
        WHEN l.longitud_onda_nm <= 1e6 THEN 'Infrarrojo'
        ELSE 'Microondas/Radio'
    END                                                             AS region_espectral,
    l.aki_s1,
    LOG10(NULLIF(l.aki_s1, 0))                                     AS log10_aki,
    (l.energia_superior_cm1 - l.energia_inferior_cm1) / 8065.543937 AS energia_foton_ev,
    l.codigo_tipo_transicion,
    t.es_permitida,
    l.codigo_exactitud,
    ex.orden                                                       AS orden_exactitud
FROM linea_espectral l
JOIN espectro         e  ON e.id_espectro = l.id_espectro
JOIN elemento         el ON el.id_elemento = e.id_elemento
JOIN tipo_transicion  t  ON t.codigo = l.codigo_tipo_transicion
LEFT JOIN exactitud   ex ON ex.codigo = l.codigo_exactitud;

-- ============================================================================
-- Fin del esquema. 9 tablas + 1 vista, todas vacias. Sin datos.
-- Siguiente paso: notebooks/05_pipeline_etl_mysql.ipynb
-- ============================================================================
